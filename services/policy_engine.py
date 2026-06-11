from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from schemas.economics_schema import EconomicsRequestIn, RouteEstimate
from config import settings

@dataclass
class PolicyResult:
    route: RouteEstimate
    budget_status: str
    policy_flags: list
    rejection_reason: Optional[str] = None

class PolicyEngine:
    def __init__(self):
        self.near_budget_threshold = settings.default_near_budget_threshold
        self.async_savings_threshold = settings.default_async_savings_threshold

    def apply_policies(self, request, routes):
        cap = request.job_budget_cap or request.workspace_budget_cap
        sync_routes = [r for r in routes if not r.is_async_batch]
        cheapest_sync = min((r.estimated_base_cost for r in sync_routes), default=None)
        results = []
        for route in routes:
            flags, rejection_reason, budget_status = [], None, "safe"
            if cap and route.estimated_high_cost > cap:
                budget_status = "blocked"
                rejection_reason = f"High cost ${route.estimated_high_cost:.2f} exceeds cap ${cap:.2f}."
                flags.append("HARD_BUDGET_BLOCK")
            elif cap and route.estimated_high_cost >= cap * self.near_budget_threshold:
                budget_status = "warning"
                flags.append("NEAR_BUDGET_WARNING")
            if route.is_async_batch and cheapest_sync and cheapest_sync > 0:
                if (cheapest_sync - route.estimated_base_cost) / cheapest_sync >= self.async_savings_threshold:
                    flags.append("ASYNC_SAVINGS_RECOMMENDED")
            if route.confidence_class == "low" and cap and route.estimated_high_cost >= cap * 0.7:
                flags.append("UNCERTAINTY_REVIEW_REQUIRED")
            results.append(PolicyResult(
                route=route.model_copy(update={"budget_status": budget_status}),
                budget_status=budget_status, policy_flags=flags, rejection_reason=rejection_reason,
            ))
        return results
