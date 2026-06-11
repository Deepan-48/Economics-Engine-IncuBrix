from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from schemas.economics_schema import EconomicsRequestIn, RouteEstimate, LatencyMode, BudgetMode

WEIGHTS = {"cost_fit": 0.45, "budget_safety": 0.20, "latency_fit": 0.15, "quality_aff": 0.10, "confidence": 0.10}

@dataclass
class RankedRoute:
    route: RouteEstimate
    score: float
    policy_flags: list
    rejection_reason: Optional[str] = None

class RouteRanker:
    def rank(self, request, policy_results):
        eligible = [pr for pr in policy_results if pr.budget_status != "blocked"]
        blocked  = [pr for pr in policy_results if pr.budget_status == "blocked"]
        eligible_routes = [pr.route for pr in eligible]
        cap = request.job_budget_cap or request.workspace_budget_cap
        costs = [r.estimated_base_cost for r in eligible_routes]
        mn, mx = (min(costs), max(costs)) if costs else (0, 1)

        ranked = []
        for pr in eligible:
            r = pr.route
            cf = (mx - r.estimated_base_cost) / (mx - mn) if mx != mn else 1.0
            bs = max(0.0, min(1.0, (cap - r.estimated_high_cost) / cap)) if cap else 0.8
            lf = (1.0 if r.is_async_batch else 0.6) if request.latency_mode == LatencyMode.async_ok else (0.3 if r.is_async_batch else 1.0) if request.latency_mode.value == "fastest" else 0.7
            qa = {"low": 1.0, "medium": 0.6, "high": 0.3}.get(r.cost_class, 0.5)
            co = {"high": 1.0, "medium": 0.6, "low": 0.3}.get(r.confidence_class, 0.5)
            score = round(WEIGHTS["cost_fit"]*cf + WEIGHTS["budget_safety"]*bs + WEIGHTS["latency_fit"]*lf + WEIGHTS["quality_aff"]*qa + WEIGHTS["confidence"]*co, 4)
            ranked.append(RankedRoute(route=r.model_copy(update={"final_score": score}), score=score, policy_flags=pr.policy_flags))

        ranked.sort(key=lambda r: r.score, reverse=True)
        ranked += [RankedRoute(route=pr.route.model_copy(update={"final_score": 0.0}), score=0.0, policy_flags=pr.policy_flags, rejection_reason=pr.rejection_reason) for pr in blocked]
        return ranked

    def build_response_parts(self, ranked):
        eligible = [r for r in ranked if r.route.budget_status != "blocked"]
        if not eligible: return None, []
        return eligible[0].route, [r.route for r in eligible[1:3]]
