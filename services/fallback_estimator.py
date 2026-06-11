from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from schemas.economics_schema import EconomicsRequestIn, RouteEstimate

@dataclass
class FallbackEstimate:
    primary_provider: str
    primary_base_cost: float
    retry_cost: float
    fallback_provider: Optional[str]
    fallback_cost: Optional[float]
    total_worst_case: float
    explanation: str

class FallbackEstimator:
    RETRY_FACTOR = 0.6
    def estimate(self, request, recommended, alternatives):
        pc = recommended.estimated_base_cost
        retry = round(pc * self.RETRY_FACTOR, 4)
        eligible = [r for r in alternatives if r.budget_status != "blocked"]
        fb_provider, fb_cost = None, None
        if eligible:
            fb = min(eligible, key=lambda r: r.estimated_base_cost)
            fb_provider, fb_cost = fb.provider, fb.estimated_base_cost
        worst = round(pc + retry + (fb_cost or 0), 4)
        parts = [f"Primary: {recommended.provider} at ${pc:.2f}.", f"Retry: ${retry:.2f}."]
        if fb_provider: parts.append(f"Fallback to {fb_provider}: ${fb_cost:.2f}.")
        parts.append(f"Worst-case: ${worst:.2f}.")
        return FallbackEstimate(recommended.provider, pc, retry, fb_provider, fb_cost, worst, " ".join(parts))
