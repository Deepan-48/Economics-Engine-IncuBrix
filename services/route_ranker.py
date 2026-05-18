"""
services/route_ranker.py

Ranks eligible routes using the weighted economic score from PRD Section 11.2:

  economic_score = (cost_fit      × 0.45)
                 + (budget_safety × 0.20)
                 + (latency_fit   × 0.15)
                 + (quality_aff   × 0.10)
                 + (confidence    × 0.10)

Only routes with budget_status != 'blocked' are eligible for recommendation.
Returns: recommended route + up to 2 alternatives.

Satisfies: ECO-FR-040, ECO-FR-041, ECO-FR-042, ECO-FR-044
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from schemas.economics_schema import EconomicsRequestIn, RouteEstimate, LatencyMode, BudgetMode
from services.policy_engine import PolicyResult


@dataclass
class RankedRoute:
    route: RouteEstimate
    score: float
    policy_flags: list[str]
    rejection_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Scoring component functions  (each returns 0.0 – 1.0)
# ---------------------------------------------------------------------------

def _cost_fit_score(route: RouteEstimate, all_eligible: list[RouteEstimate]) -> float:
    """
    Inversely proportional to base cost.
    Cheapest route gets 1.0; most expensive gets 0.0.
    """
    costs = [r.estimated_base_cost for r in all_eligible]
    min_c, max_c = min(costs), max(costs)
    if max_c == min_c:
        return 1.0
    return (max_c - route.estimated_base_cost) / (max_c - min_c)


def _budget_safety_score(route: RouteEstimate, budget_cap: Optional[float]) -> float:
    """
    How much headroom does this route leave under the cap?
    No cap → assume it's safe → 0.8 (not perfect since we can't verify)
    """
    if budget_cap is None or budget_cap == 0:
        return 0.8
    headroom = budget_cap - route.estimated_high_cost
    ratio = headroom / budget_cap
    return max(0.0, min(1.0, ratio))


def _latency_fit_score(route: RouteEstimate, latency_mode: LatencyMode) -> float:
    """
    async_ok prefers async routes; fastest penalises async.
    """
    if latency_mode == LatencyMode.async_ok:
        return 1.0 if route.is_async_batch else 0.6
    elif latency_mode == LatencyMode.fastest:
        return 0.3 if route.is_async_batch else 1.0
    else:  # balanced
        return 0.7


def _quality_affordability_score(route: RouteEstimate) -> float:
    """
    Lower cost_class → better affordability score.
    """
    return {"low": 1.0, "medium": 0.6, "high": 0.3}.get(route.cost_class, 0.5)


def _confidence_score(route: RouteEstimate) -> float:
    """High confidence in estimate → higher score."""
    return {"high": 1.0, "medium": 0.6, "low": 0.3}.get(route.confidence_class, 0.5)


# ---------------------------------------------------------------------------
# Main ranker
# ---------------------------------------------------------------------------

class RouteRanker:
    """
    Ranks policy-cleared routes by economic score.
    Blocked routes are excluded from recommendation but still returned for transparency.
    """

    WEIGHTS = {
        "cost_fit":    0.45,
        "budget_safety": 0.20,
        "latency_fit": 0.15,
        "quality_aff": 0.10,
        "confidence":  0.10,
    }

    def rank(
        self,
        request: EconomicsRequestIn,
        policy_results: list[PolicyResult],
    ) -> list[RankedRoute]:
        """
        Score and sort eligible routes. Blocked routes get score=0 and go last.
        Returns all routes sorted best → worst.
        """
        eligible = [
            pr for pr in policy_results if pr.budget_status != "blocked"
        ]
        blocked  = [
            pr for pr in policy_results if pr.budget_status == "blocked"
        ]

        eligible_routes = [pr.route for pr in eligible]
        budget_cap = request.job_budget_cap or request.workspace_budget_cap

        ranked_eligible: list[RankedRoute] = []
        for pr in eligible:
            route = pr.route
            score = (
                self.WEIGHTS["cost_fit"]    * _cost_fit_score(route, eligible_routes)
                + self.WEIGHTS["budget_safety"] * _budget_safety_score(route, budget_cap)
                + self.WEIGHTS["latency_fit"]   * _latency_fit_score(route, request.latency_mode)
                + self.WEIGHTS["quality_aff"]   * _quality_affordability_score(route)
                + self.WEIGHTS["confidence"]    * _confidence_score(route)
            )
            score = round(score, 4)

            ranked_eligible.append(
                RankedRoute(
                    route=route.model_copy(update={"final_score": score}),
                    score=score,
                    policy_flags=pr.policy_flags,
                )
            )

        # Sort eligible best → worst
        ranked_eligible.sort(key=lambda r: r.score, reverse=True)

        # Append blocked routes at the end (score=0)
        ranked_blocked = [
            RankedRoute(
                route=pr.route.model_copy(update={"final_score": 0.0}),
                score=0.0,
                policy_flags=pr.policy_flags,
                rejection_reason=pr.rejection_reason,
            )
            for pr in blocked
        ]

        return ranked_eligible + ranked_blocked

    def build_response_parts(
        self,
        ranked: list[RankedRoute],
    ) -> tuple[Optional[RouteEstimate], list[RouteEstimate]]:
        """
        Split ranked list into (recommended, alternatives).
        recommended = rank[0] if not blocked
        alternatives = rank[1] and rank[2] if they exist and are not blocked
        """
        eligible = [r for r in ranked if r.route.budget_status != "blocked"]

        if not eligible:
            return None, []

        recommended = eligible[0].route
        alternatives = [r.route for r in eligible[1:3]]  # up to 2
        return recommended, alternatives
