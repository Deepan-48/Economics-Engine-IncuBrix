"""
api_v2/estimate_router.py - Main estimate endpoint
"""
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.database import get_db
from schemas_v2.economics_v2_schema import (
    EstimateRequestV2, FullEstimateResponse, OverrideV2In,
    BudgetReservationIn,
)
from models_v2.models_v2 import EconomicsEstimateV2
from services_v2.gateway.gateway_service import GatewayService
from services_v2.pricing.pricing_intelligence_service import PricingIntelligenceService
from services_v2.estimator.estimation_engine_v2 import EstimationEngineV2
from services_v2.budget.budget_guardrail_service import BudgetGuardrailService
from services_v2.margin.margin_policy_service import MarginPolicyServiceV2
from services_v2.decision.route_decision_service import RouteDecisionServiceV2
from services_v2.batch.batch_optimization_service import BatchOptimizationService
from services_v2.analytics.analytics_service_v2 import AnalyticsServiceV2
from services_v2.integration.integration_adapter import IntegrationAdapter

router = APIRouter(prefix="/api/economics/v2", tags=["Economics v2"])


def _run_pipeline(request: EstimateRequestV2, db: Session) -> dict:
    gateway = GatewayService()

    # idempotency check
    if request.idempotency_key:
        cached = gateway.check_idempotency(request.idempotency_key, db)
        if cached:
            return {"cached": True, "result": cached}

    fingerprint = gateway.build_fingerprint(request)

    profiles = PricingIntelligenceService(db).get_active_profiles()
    if not profiles:
        raise HTTPException(status_code=503, detail="No active pricing profiles. Run seed script.")

    estimates = EstimationEngineV2().estimate_all_routes(request, profiles)

    budget_svc = BudgetGuardrailService()
    margin_svc = MarginPolicyServiceV2()

    for i, e in enumerate(estimates):
        budget_result = budget_svc.check(e, request.job_budget_cap, request.workspace_budget_cap, request.campaign_budget_cap)
        estimates[i] = e.model_copy(update={"budget_status": budget_result["budget_status"]})
        if request.markup_mode:
            margin_result = margin_svc.evaluate(e, request.markup_mode, request.price_to_customer, request.target_margin_percent)
            estimates[i] = estimates[i].model_copy(update={"margin_status": margin_result["margin_status"]})

    ranker = RouteDecisionServiceV2()
    ranked = ranker.rank(request, estimates)
    recommended, alternatives, blocked = ranker.build_response(ranked)

    batch_rec = BatchOptimizationService().evaluate(estimates, request.latency_mode)

    savings_delta = None
    if recommended and alternatives:
        savings_delta = round(alternatives[0].estimated_base_cost - recommended.estimated_base_cost, 4)

    margin_info = None
    if recommended and request.markup_mode:
        margin_info = margin_svc.evaluate(recommended, request.markup_mode, request.price_to_customer, request.target_margin_percent)

    req_status = "blocked" if recommended is None else "completed"
    blocked_reason = None
    if recommended is None:
        if margin_info and margin_info.get("is_margin_blocked"):
            blocked_reason = margin_info["explanation"]
        else:
            blocked_reason = "All routes exceeded budget policy. Try reducing batch size or using async_ok."

    analytics = AnalyticsServiceV2(db)

    for e in estimates:
        db_est = EconomicsEstimateV2(
            request_id=request.request_id,
            correlation_id=request.correlation_id,
            idempotency_key=request.idempotency_key if (recommended is not None and e.provider_key == recommended.provider_key) else None,
            job_fingerprint=fingerprint,
            workspace_id=request.workspace_id,
            project_id=request.project_id,
            campaign_id=request.campaign_id,
            provider_key=e.provider_key,
            model_key=e.model_key,
            execution_mode=e.execution_mode,
            estimated_low_cost=e.estimated_low_cost,
            estimated_base_cost=e.estimated_base_cost,
            estimated_high_cost=e.estimated_high_cost,
            currency=e.currency,
            confidence_class=e.confidence_class,
            cost_class=e.cost_class,
            budget_status=e.budget_status,
            margin_status=e.margin_status,
            final_score=e.final_score,
            is_recommended=(recommended is not None and e.provider_key == recommended.provider_key),
            explanation=e.explanation,
            cost_components=[c.model_dump() if hasattr(c, 'model_dump') else c for c in (e.cost_components or [])],
            cost_drivers=e.cost_drivers,
            pricing_profile_version=e.pricing_profile_versions[0] if e.pricing_profile_versions else None,
            is_async_batch=e.is_async_batch,
            async_savings_percent=e.async_savings_percent,
            retry_exposure=e.retry_exposure,
            per_output_cost=e.per_output_cost,
            simulation_mode=request.simulation_mode,
        )
        db.add(db_est)
    db.commit()

    if recommended:
        analytics.estimate_created(request.request_id, request.correlation_id,
                                    request.workspace_id, recommended.provider_key,
                                    recommended.estimated_base_cost, recommended.budget_status)
        if batch_rec.get("batch_recommended") and batch_rec.get("estimated_savings", 0) > 0:
            analytics.batch_savings_recommended(
                request.request_id, request.correlation_id, request.workspace_id,
                batch_rec["recommended_provider"], batch_rec["estimated_savings"], batch_rec["savings_percent"],
            )

    cap = request.job_budget_cap or request.workspace_budget_cap or request.campaign_budget_cap
    for e in [e for e in estimates if e.budget_status == "blocked_hard_cap"]:
        analytics.budget_blocked(request.request_id, request.correlation_id,
                                  request.workspace_id, e.provider_key, e.estimated_high_cost, cap)

    response = FullEstimateResponse(
        request_id=request.request_id,
        correlation_id=request.correlation_id,
        recommended_route=recommended,
        alternatives=alternatives,
        blocked_routes=blocked,
        all_routes=ranked,
        request_status=req_status,
        blocked_reason=blocked_reason,
        savings_delta_vs_next=savings_delta,
        margin_simulation=margin_info,
        batch_recommendation=batch_rec,
        simulation_mode=request.simulation_mode,
        job_fingerprint=fingerprint,
    )

    adapter = IntegrationAdapter()
    return {
        "response":         response,
        "routing_adapter":  adapter.routing_response(response),
        "preflight_adapter": adapter.execution_preflight(response),
        "billing_adapter":  adapter.billing_export(response),
    }


@router.post("/estimate", status_code=201)
def create_estimate(request: EstimateRequestV2, db: Session = Depends(get_db)):
    result = _run_pipeline(request, db)
    if result.get("cached"):
        return result["result"]
    resp = result["response"]
    out = resp.model_dump()
    out["routing_adapter"]   = result["routing_adapter"]
    out["preflight_adapter"] = result["preflight_adapter"]
    out["billing_adapter"]   = result["billing_adapter"]
    return out


@router.post("/simulate", status_code=200)
def simulate_estimate(request: EstimateRequestV2, db: Session = Depends(get_db)):
    simulated = request.model_copy(update={"simulation_mode": True})
    result = _run_pipeline(simulated, db)
    resp = result["response"]
    out = resp.model_dump()
    out["routing_adapter"]   = result["routing_adapter"]
    out["preflight_adapter"] = result["preflight_adapter"]
    return out


@router.get("/estimate/{estimate_id}/breakdown")
def get_estimate_breakdown(estimate_id: str, db: Session = Depends(get_db)):
    estimates = db.query(EconomicsEstimateV2).filter(
        EconomicsEstimateV2.request_id == estimate_id
    ).all()
    if not estimates:
        raise HTTPException(status_code=404, detail="Estimate not found.")
    return {
        "request_id": estimate_id,
        "routes": [e.to_dict() for e in estimates],
    }


@router.post("/decision/{decision_id}/override", status_code=201)
def override_decision(decision_id: str, payload: OverrideV2In, db: Session = Depends(get_db)):
    from models_v2.models_v2 import EconomicsEstimateV2
    est = db.query(EconomicsEstimateV2).filter(
        EconomicsEstimateV2.request_id == decision_id,
        EconomicsEstimateV2.is_recommended == True,
    ).first()

    original = est.provider_key if est else "unknown"

    analytics = AnalyticsServiceV2(db)
    analytics.override_submitted(decision_id, None, None, original, payload.override_provider, payload.override_reason)

    return {
        "decision_id":      decision_id,
        "original_provider": original,
        "override_provider": payload.override_provider,
        "override_reason":   payload.override_reason,
        "authorized_by":     payload.authorized_by,
        "stored":            True,
    }
