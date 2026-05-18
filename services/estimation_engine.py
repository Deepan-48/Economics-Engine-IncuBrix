"""
services/estimation_engine.py

Core estimation logic.
For each active provider, calls cost_normalizer, classifies the result,
and returns a list of RouteEstimate objects ready for ranking.

Satisfies: ECO-FR-020, ECO-FR-021, ECO-FR-023, ECO-FR-024
"""

from __future__ import annotations
from typing import Optional
from schemas.economics_schema import (
    EconomicsRequestIn,
    RouteEstimate,
    DurationClass,
    QualityBar,
)
from services.cost_normalizer import normalize_cost


# ---------------------------------------------------------------------------
# Cost / confidence classification helpers
# ---------------------------------------------------------------------------

def _classify_cost(base_cost: float, batch_size: int) -> str:
    """
    Classify absolute cost into low / medium / high.
    Thresholds are per-job (total cost for the batch).
    """
    if base_cost < 5.0:
        return "low"
    elif base_cost < 50.0:
        return "medium"
    return "high"


def _classify_confidence(profile: dict, quality_bar: QualityBar) -> str:
    """
    Confidence is based on how well we know this provider's pricing.
    - OpenAI (per_second) → published rates → high confidence
    - Runway (credits)    → published credits → high confidence
    - fal (flat)          → model-level pricing, varies → medium
    - Replicate (runtime) → runtime varies → medium/low
    - PiAPI               → account mode affects it → medium
    """
    pricing_unit = profile.get("pricing_unit", "")
    if pricing_unit == "per_second":
        return "high"
    elif pricing_unit == "credits":
        return "high" if quality_bar != QualityBar.premium else "medium"
    elif pricing_unit == "flat":
        return "medium"
    elif pricing_unit == "runtime":
        return "medium" if profile.get("base_assumptions", {}) else "low"
    elif pricing_unit == "credits_account_mode":
        return "medium"
    return "low"


def _build_explanation(
    provider_key: str,
    cost_result: dict,
    quality_bar: QualityBar,
    latency_mode_str: str,
    budget_status: str,
    job_budget_cap: Optional[float],
) -> str:
    """Generate a human-readable explanation for this route estimate."""
    base = cost_result["base_cost"]
    low  = cost_result["low_cost"]
    high = cost_result["high_cost"]

    parts = [
        f"{provider_key.upper()} estimated at ${base:.2f} "
        f"(range ${low:.2f}–${high:.2f})."
    ]

    if cost_result.get("is_async_batch"):
        pct = cost_result.get("async_savings_percent", 0)
        parts.append(
            f"Async/batch mode applied ({pct}% discount vs synchronous execution)."
        )

    if budget_status == "blocked":
        parts.append(
            f"BLOCKED: estimated high cost ${high:.2f} exceeds "
            f"policy cap ${job_budget_cap:.2f}."
        )
    elif budget_status == "warning":
        parts.append(
            f"WARNING: estimate is within 15% of the budget cap ${job_budget_cap:.2f}."
        )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Main estimation engine
# ---------------------------------------------------------------------------

class EstimationEngine:
    """
    Given an EconomicsRequestIn and a list of active pricing profiles,
    returns a RouteEstimate for each provider.
    """

    def estimate_all_routes(
        self,
        request: EconomicsRequestIn,
        active_profiles: list[dict],
    ) -> list[RouteEstimate]:
        """
        Estimate cost for every active provider.
        Returns list of RouteEstimate (not yet ranked or policy-filtered).
        """
        results: list[RouteEstimate] = []

        for profile in active_profiles:
            try:
                cost_result = normalize_cost(
                    profile=profile,
                    duration_class=request.duration_class,
                    quality_bar=request.quality_bar,
                    latency_mode=request.latency_mode,
                    batch_size=request.batch_size,
                )
            except Exception as e:
                # Skip broken profiles rather than crashing the whole engine
                print(f"[EstimationEngine] skipping {profile.get('provider_key')}: {e}")
                continue

            provider_key = profile["provider_key"]
            base = cost_result["base_cost"]
            high = cost_result["high_cost"]
            confidence = _classify_confidence(profile, request.quality_bar)
            cost_class  = _classify_cost(base, request.batch_size)

            # Preliminary budget status (policy engine will refine this)
            budget_status = "safe"
            effective_cap = request.job_budget_cap or request.workspace_budget_cap
            if effective_cap is not None:
                if high > effective_cap:
                    budget_status = "blocked"
                elif high >= effective_cap * 0.85:
                    budget_status = "warning"

            explanation = _build_explanation(
                provider_key=provider_key,
                cost_result=cost_result,
                quality_bar=request.quality_bar,
                latency_mode_str=request.latency_mode.value,
                budget_status=budget_status,
                job_budget_cap=effective_cap,
            )

            results.append(
                RouteEstimate(
                    provider=provider_key,
                    estimated_base_cost=base,
                    estimated_low_cost=cost_result["low_cost"],
                    estimated_high_cost=high,
                    budget_status=budget_status,
                    cost_class=cost_class,
                    confidence_class=confidence,
                    explanation=explanation,
                    is_async_batch=cost_result.get("is_async_batch", False),
                    async_savings_percent=cost_result.get("async_savings_percent"),
                )
            )

        return results
