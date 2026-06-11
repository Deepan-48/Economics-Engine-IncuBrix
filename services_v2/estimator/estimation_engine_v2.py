"""
services_v2/estimator/estimation_engine_v2.py

ECO2-EST-001 to ECO2-EST-005
"""

from __future__ import annotations
from schemas_v2.economics_v2_schema import EstimateRequestV2, EstimateResultV2, QualityBar
from services_v2.normalization.normalization_service import normalize_provider_cost

RETRY_MULTIPLIER      = 0.6
EXPECTED_FAILURE_RATE = 0.05
FORMULA_VERSION       = "v2.0"


def _confidence(profile: dict, quality_bar: QualityBar) -> str:
    source = profile.get("source_type", "manual")
    if source in ("provider_api", "invoice_actual"):
        return "high"
    rcs = profile.get("rate_cards", [])
    unit_type = rcs[0].get("unit_type", "") if rcs else ""
    if unit_type in ("per_second", "credits") and source == "manual":
        return "high"
    if quality_bar.value == "premium":
        return "medium"
    return "medium"


def _cost_class(base: float) -> str:
    if base < 5.0:
        return "low"
    elif base < 50.0:
        return "medium"
    return "high"


def _cost_drivers(unit_type: str) -> list[dict]:
    if unit_type == "per_second":
        return [
            {"driver": "duration_seconds",   "contribution_percent": 55},
            {"driver": "batch_size",          "contribution_percent": 35},
            {"driver": "quality_multiplier",  "contribution_percent": 10},
        ]
    elif unit_type in ("credits",):
        return [
            {"driver": "credits_consumed",    "contribution_percent": 60},
            {"driver": "batch_size",          "contribution_percent": 30},
            {"driver": "quality_tier",        "contribution_percent": 10},
        ]
    elif unit_type == "per_runtime_second":
        return [
            {"driver": "runtime_seconds",     "contribution_percent": 50},
            {"driver": "hardware_class",      "contribution_percent": 35},
            {"driver": "batch_size",          "contribution_percent": 15},
        ]
    return [
        {"driver": "base_rate",  "contribution_percent": 70},
        {"driver": "batch_size", "contribution_percent": 30},
    ]


def _explanation(provider: str, norm: dict, budget_status: str, cap, is_async: bool) -> str:
    base  = norm["async_base_cost"] if is_async else norm["base_cost"]
    low   = norm["low_cost"]
    high  = norm["high_cost"]
    parts = [f"{provider.upper()} est. ${base:.2f} (range ${low:.2f}–${high:.2f})."]
    if is_async:
        pct = norm.get("async_savings_percent", 0)
        parts.append(f"Async/batch saves {pct}% vs sync.")
    if budget_status == "blocked_hard_cap" and cap:
        parts.append(f"Blocked: high ${high:.2f} > cap ${cap:.2f}.")
    elif budget_status == "warn_near_cap" and cap:
        parts.append(f"Warning: near cap ${cap:.2f}.")
    return " ".join(parts)


class EstimationEngineV2:

    def estimate_all_routes(
        self,
        request: EstimateRequestV2,
        active_profiles: list[dict],
    ) -> list[EstimateResultV2]:

        results = []
        cap = request.job_budget_cap or request.workspace_budget_cap or request.campaign_budget_cap

        if request.candidate_routes:
            keys = {r.provider_key for r in request.candidate_routes}
            profiles = [p for p in active_profiles if p["provider_key"] in keys]
        else:
            profiles = active_profiles

        for profile in profiles:
            try:
                norm = normalize_provider_cost(
                    profile=profile,
                    duration_class=request.duration_class,
                    quality_bar=request.quality_bar,
                    latency_mode=request.latency_mode,
                    batch_size=request.batch_size,
                    variant_count=request.variant_count,
                )
            except Exception as e:
                print(f"[EstimatorV2] skip {profile.get('provider_key')}: {e}")
                continue

            provider = profile["provider_key"]
            is_async  = norm["is_async_batch"]
            base_cost = norm["async_base_cost"] if is_async else norm["base_cost"]
            low_cost  = round(base_cost * profile.get("default_uncertainty_multiplier_low", 0.9), 4)
            high_cost = round(base_cost * profile.get("default_uncertainty_multiplier_high", 1.2), 4)

            confidence = _confidence(profile, request.quality_bar)
            cost_cls   = _cost_class(base_cost)

            budget_status = "safe"
            if cap is not None:
                if high_cost > cap:
                    budget_status = "blocked_hard_cap"
                elif high_cost >= cap * 0.85:
                    budget_status = "warn_near_cap"

            retry_exposure  = round(base_cost * RETRY_MULTIPLIER * EXPECTED_FAILURE_RATE, 4)
            total_outputs   = request.batch_size * request.variant_count
            per_output_cost = round(base_cost / total_outputs, 4) if total_outputs > 0 else None

            components = norm.get("cost_components", [])
            unit_type  = components[0]["unit_type"] if components else "unknown"
            drivers    = _cost_drivers(unit_type)

            profile_ver = f"{provider}:{profile.get('profile_version', 1)}"

            results.append(EstimateResultV2(
                request_id=request.request_id,
                pricing_profile_versions=[profile_ver],
                provider_key=provider,
                model_key=profile.get("model_key", "default"),
                execution_mode="batch" if is_async else "sync",
                estimated_low_cost=low_cost,
                estimated_base_cost=base_cost,
                estimated_high_cost=high_cost,
                currency=request.currency,
                confidence_class=confidence,
                cost_class=cost_cls,
                budget_status=budget_status,
                explanation=_explanation(provider, norm, budget_status, cap, is_async),
                cost_components=components,
                cost_drivers=drivers,
                is_async_batch=is_async,
                async_savings_percent=norm.get("async_savings_percent"),
                retry_exposure=retry_exposure,
                per_output_cost=per_output_cost,
            ))

        return results
