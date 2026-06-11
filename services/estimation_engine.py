from __future__ import annotations
from schemas.economics_schema import EconomicsRequestIn, RouteEstimate, QualityBar
from services.cost_normalizer import normalize_cost

def _classify_cost(base):
    if base < 5.0: return "low"
    elif base < 50.0: return "medium"
    return "high"

def _classify_confidence(profile, quality_bar):
    pu = profile.get("pricing_unit", "")
    if pu == "per_second": return "high"
    elif pu == "credits": return "high" if quality_bar != QualityBar.premium else "medium"
    return "medium"

def _explanation(provider, cost_result, budget_status, cap):
    base, low, high = cost_result["base_cost"], cost_result["low_cost"], cost_result["high_cost"]
    parts = [f"{provider.upper()} estimated at ${base:.2f} (range ${low:.2f}-${high:.2f})."]
    if cost_result.get("is_async_batch"):
        parts.append(f"Async/batch mode applied ({cost_result.get('async_savings_percent',0)}% discount).")
    if budget_status == "blocked":
        parts.append(f"BLOCKED: high cost ${high:.2f} exceeds cap ${cap:.2f}.")
    elif budget_status == "warning":
        parts.append(f"WARNING: estimate near cap ${cap:.2f}.")
    return " ".join(parts)

class EstimationEngine:
    def estimate_all_routes(self, request, active_profiles):
        results = []
        for profile in active_profiles:
            try:
                cost = normalize_cost(profile, request.duration_class, request.quality_bar, request.latency_mode, request.batch_size)
            except Exception as e:
                print(f"[EstimationEngine] skip {profile.get('provider_key')}: {e}")
                continue
            pk = profile["provider_key"]
            base, high = cost["base_cost"], cost["high_cost"]
            cap = request.job_budget_cap or request.workspace_budget_cap
            budget_status = "safe"
            if cap:
                if high > cap: budget_status = "blocked"
                elif high >= cap * 0.85: budget_status = "warning"
            results.append(RouteEstimate(
                provider=pk, estimated_base_cost=base,
                estimated_low_cost=cost["low_cost"], estimated_high_cost=high,
                budget_status=budget_status,
                cost_class=_classify_cost(base),
                confidence_class=_classify_confidence(profile, request.quality_bar),
                explanation=_explanation(pk, cost, budget_status, cap),
                is_async_batch=cost.get("is_async_batch", False),
                async_savings_percent=cost.get("async_savings_percent"),
            ))
        return results
