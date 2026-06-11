"""
services_v2/batch/batch_optimization_service.py
ECO2-BAT-001 to ECO2-BAT-004
"""
from __future__ import annotations
from schemas_v2.economics_v2_schema import EstimateResultV2, LatencyMode

THRESHOLD = 0.15


class BatchOptimizationService:

    def evaluate(self, estimates: list[EstimateResultV2], latency_mode: LatencyMode) -> dict:
        sync_routes  = [e for e in estimates if not e.is_async_batch]
        async_routes = [e for e in estimates if e.is_async_batch]

        if not sync_routes or not async_routes:
            return {"batch_recommended": False, "reason": "No sync/async pair available.", "sync_vs_async": []}

        cheapest_sync  = min(sync_routes,  key=lambda e: e.estimated_base_cost)
        cheapest_async = min(async_routes, key=lambda e: e.estimated_base_cost)

        savings = cheapest_sync.estimated_base_cost - cheapest_async.estimated_base_cost
        ratio   = savings / cheapest_sync.estimated_base_cost if cheapest_sync.estimated_base_cost > 0 else 0

        batch_recommended = ratio >= THRESHOLD and latency_mode != LatencyMode.fastest
        deadline_risk = latency_mode == LatencyMode.fastest and ratio >= THRESHOLD

        comparison = []
        for e in sync_routes[:3]:
            comparison.append({"provider": e.provider_key, "mode": "sync", "base_cost": e.estimated_base_cost})
        for e in async_routes[:3]:
            comparison.append({
                "provider": e.provider_key, "mode": "async_batch",
                "base_cost": e.estimated_base_cost,
                "savings_vs_cheapest_sync": round(cheapest_sync.estimated_base_cost - e.estimated_base_cost, 4),
            })

        return {
            "batch_recommended":    batch_recommended,
            "estimated_savings":    round(savings, 4),
            "savings_percent":      round(ratio * 100, 1),
            "deadline_risk":        deadline_risk,
            "recommended_provider": cheapest_async.provider_key if batch_recommended else cheapest_sync.provider_key,
            "sync_vs_async":        comparison,
        }
