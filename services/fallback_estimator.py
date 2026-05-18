"""
services/fallback_estimator.py

Estimates retry and fallback cost exposure for a job.
If the recommended provider fails mid-job, what would it cost
to retry on the same provider or fall back to the next best one?

ECO-FR-022
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from schemas.economics_schema import EconomicsRequestIn, RouteEstimate


@dataclass
class FallbackEstimate:
    primary_provider: str
    primary_base_cost: float
    retry_cost: float           # cost of retrying on same provider
    fallback_provider: Optional[str]
    fallback_cost: Optional[float]
    total_worst_case: float     # primary + retry + fallback
    explanation: str


class FallbackEstimator:
    # partial retry assumed at 60% of original cost
    RETRY_FACTOR = 0.6

    def estimate(
        self,
        request: EconomicsRequestIn,
        recommended: RouteEstimate,
        alternatives: list[RouteEstimate],
    ) -> FallbackEstimate:

        primary_cost = recommended.estimated_base_cost
        retry_cost = round(primary_cost * self.RETRY_FACTOR, 4)

        fallback_provider = None
        fallback_cost = None

        # pick cheapest non-blocked alternative as fallback
        eligible = [r for r in alternatives if r.budget_status != "blocked"]
        if eligible:
            fallback = min(eligible, key=lambda r: r.estimated_base_cost)
            fallback_provider = fallback.provider
            fallback_cost = fallback.estimated_base_cost

        worst_case = primary_cost + retry_cost
        if fallback_cost:
            worst_case = round(worst_case + fallback_cost, 4)
        else:
            worst_case = round(worst_case, 4)

        parts = [
            f"Primary: {recommended.provider} at ${primary_cost:.2f}.",
            f"Retry exposure (60% of primary): ${retry_cost:.2f}.",
        ]
        if fallback_provider:
            parts.append(f"Fallback to {fallback_provider}: ${fallback_cost:.2f}.")
        parts.append(f"Total worst-case exposure: ${worst_case:.2f}.")

        return FallbackEstimate(
            primary_provider=recommended.provider,
            primary_base_cost=primary_cost,
            retry_cost=retry_cost,
            fallback_provider=fallback_provider,
            fallback_cost=fallback_cost,
            total_worst_case=worst_case,
            explanation=" ".join(parts),
        )
