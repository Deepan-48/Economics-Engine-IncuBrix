"""
services/policy_engine.py

Applies all policy rules from PRD Section 13 to a list of RouteEstimates.
Rules (in order of precedence):
  1. Hard budget block       — reject if high_cost > cap
  2. Near-budget warning     — warn if high_cost >= 85% of cap
  3. Async-savings recommend — flag if async saves > 15% vs cheapest sync
  4. Protected-margin block  — reject if margin < target (Sprint 2; stub here)
  5. Uncertainty review      — flag for manual review if low-confidence + near cap

Satisfies: ECO-FR-030, ECO-FR-031 (warning), ECO-FR-034
"""

from __future__ import annotations
from typing import Optional
from dataclasses import dataclass

from schemas.economics_schema import EconomicsRequestIn, RouteEstimate
from config import settings


@dataclass
class PolicyResult:
    """What the policy engine decided for a single route."""
    route: RouteEstimate
    budget_status: str          # safe | warning | blocked
    policy_flags: list[str]     # list of policy codes that fired
    rejection_reason: Optional[str] = None


class PolicyEngine:
    """
    Applies budget, margin, and warning policies to route estimates.
    Returns annotated PolicyResult objects.
    """

    def __init__(self):
        self.near_budget_threshold = settings.default_near_budget_threshold
        self.async_savings_threshold = settings.default_async_savings_threshold

    def apply_policies(
        self,
        request: EconomicsRequestIn,
        routes: list[RouteEstimate],
    ) -> list[PolicyResult]:
        """
        Run all routes through policy checks.
        Returns a PolicyResult per route with updated budget_status.
        """
        effective_cap = request.job_budget_cap or request.workspace_budget_cap
        results: list[PolicyResult] = []

        # Find cheapest sync route for async savings comparison
        sync_routes = [r for r in routes if not r.is_async_batch]
        cheapest_sync_cost = min(
            (r.estimated_base_cost for r in sync_routes), default=None
        )

        for route in routes:
            flags: list[str] = []
            rejection_reason: Optional[str] = None
            budget_status = "safe"

            # ----------------------------------------------------------
            # Rule 1: Hard budget block
            # ----------------------------------------------------------
            if effective_cap is not None and route.estimated_high_cost > effective_cap:
                budget_status = "blocked"
                rejection_reason = (
                    f"Estimated high cost ${route.estimated_high_cost:.2f} exceeds "
                    f"policy cap ${effective_cap:.2f}. "
                    f"Consider a shorter duration, lower quality, or async mode."
                )
                flags.append("HARD_BUDGET_BLOCK")

            # ----------------------------------------------------------
            # Rule 2: Near-budget warning (only if not already blocked)
            # ----------------------------------------------------------
            elif (
                effective_cap is not None
                and route.estimated_high_cost >= effective_cap * self.near_budget_threshold
            ):
                budget_status = "warning"
                flags.append("NEAR_BUDGET_WARNING")

            # ----------------------------------------------------------
            # Rule 3: Async savings recommendation
            # ----------------------------------------------------------
            if (
                route.is_async_batch
                and cheapest_sync_cost is not None
                and cheapest_sync_cost > 0
            ):
                savings_ratio = (
                    cheapest_sync_cost - route.estimated_base_cost
                ) / cheapest_sync_cost
                if savings_ratio >= self.async_savings_threshold:
                    flags.append("ASYNC_SAVINGS_RECOMMENDED")

            # ----------------------------------------------------------
            # Rule 4: Protected-margin block (stub for Sprint 2)
            # ----------------------------------------------------------
            # Will be implemented in Sprint 2 when markup_mode is active

            # ----------------------------------------------------------
            # Rule 5: Uncertainty review flag
            # ----------------------------------------------------------
            if (
                route.confidence_class == "low"
                and effective_cap is not None
                and route.estimated_high_cost >= effective_cap * 0.7
            ):
                flags.append("UNCERTAINTY_REVIEW_REQUIRED")

            # Update route budget_status with policy result
            annotated_route = route.model_copy(update={"budget_status": budget_status})

            results.append(
                PolicyResult(
                    route=annotated_route,
                    budget_status=budget_status,
                    policy_flags=flags,
                    rejection_reason=rejection_reason,
                )
            )

        return results
