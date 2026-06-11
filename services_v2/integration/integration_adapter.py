"""
services_v2/integration/integration_adapter.py
ECO2-INT-001 to ECO2-INT-005
"""
from __future__ import annotations
from schemas_v2.economics_v2_schema import EstimateRequestV2, FullEstimateResponse


class IntegrationAdapter:

    def routing_response(self, response: FullEstimateResponse) -> dict:
        """Adapter for Routing service - returns machine-readable route ranking."""
        rec = response.recommended_route
        return {
            "request_id":    response.request_id,
            "correlation_id": response.correlation_id,
            "recommended": {
                "provider_key":     rec.provider_key if rec else None,
                "model_key":        rec.model_key if rec else None,
                "execution_mode":   rec.execution_mode if rec else None,
                "cost_class":       rec.cost_class if rec else None,
                "budget_status":    rec.budget_status if rec else None,
                "final_score":      rec.final_score if rec else None,
                "explanation":      rec.explanation if rec else None,
            } if rec else None,
            "alternatives": [
                {"provider_key": a.provider_key, "cost_class": a.cost_class, "budget_status": a.budget_status}
                for a in response.alternatives
            ],
            "blocked_routes": [
                {"provider_key": b.provider_key, "budget_status": b.budget_status}
                for b in response.blocked_routes
            ],
            "request_status": response.request_status,
        }

    def execution_preflight(self, response: FullEstimateResponse, reservation_id: str = None) -> dict:
        """Adapter for Execution service - preflight check before running a job."""
        rec = response.recommended_route
        can_proceed = response.request_status == "completed" and rec is not None

        return {
            "can_proceed":     can_proceed,
            "request_id":      response.request_id,
            "reservation_id":  reservation_id or response.reservation_id,
            "provider_key":    rec.provider_key if rec else None,
            "execution_mode":  rec.execution_mode if rec else None,
            "budget_status":   rec.budget_status if rec else "blocked",
            "blocked_reason":  response.blocked_reason,
            "estimated_cost":  rec.estimated_base_cost if rec else None,
        }

    def billing_export(self, response: FullEstimateResponse) -> dict:
        """Adapter for Billing service - cost allocation summary."""
        rec = response.recommended_route
        return {
            "request_id":       response.request_id,
            "provider_key":     rec.provider_key if rec else None,
            "estimated_amount": rec.estimated_base_cost if rec else None,
            "currency":         rec.currency if rec else "USD",
            "cost_components":  rec.cost_components if rec else [],
            "simulation_mode":  response.simulation_mode,
        }
