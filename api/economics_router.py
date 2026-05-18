"""
api/economics_router.py

Sprint 1 endpoints + Sprint 2 additions:
- analytics events fired on every estimate/block/override
- fallback cost exposure included in response
- margin simulation when markup_mode is provided
- savings delta vs next-best route (ECO-FR-043)
- near-budget warning (ECO-FR-031)
"""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from db.database import get_db
from schemas.economics_schema import (
    EconomicsRequestIn,
    EconomicsResponseOut,
    RouteEstimate,
    OverrideRequestIn,
    OverrideResponseOut,
)
from models.economics_request import EconomicsRequest
from models.economics_decision import EconomicsDecision, EconomicsOverride
from services.pricing_registry_service import PricingRegistryService
from services.estimation_engine import EstimationEngine
from services.policy_engine import PolicyEngine
from services.route_ranker import RouteRanker
from services.fallback_estimator import FallbackEstimator
from services.margin_engine import MarginEngine
from services.analytics_service import AnalyticsService
from config import settings

router = APIRouter(prefix=settings.api_prefix, tags=["Economics Engine"])


def _run_economics_pipeline(request: EconomicsRequestIn, db: Session) -> dict:

    registry = PricingRegistryService(db)
    profiles = registry.get_all_active()
    if not profiles:
        raise HTTPException(
            status_code=503,
            detail="No active pricing profiles found. Run the seed script.",
        )

    engine = EstimationEngine()
    route_estimates = engine.estimate_all_routes(request, profiles)

    policy = PolicyEngine()
    policy_results = policy.apply_policies(request, route_estimates)

    ranker = RouteRanker()
    ranked = ranker.rank(request, policy_results)
    recommended, alternatives = ranker.build_response_parts(ranked)

    all_routes = [r.route for r in ranked]

    # savings delta vs next-best (ECO-FR-043)
    savings_delta = None
    if recommended and alternatives:
        savings_delta = round(
            alternatives[0].estimated_base_cost - recommended.estimated_base_cost, 4
        )

    # fallback exposure (ECO-FR-022)
    fallback_info = None
    if recommended:
        fe = FallbackEstimator()
        fb = fe.estimate(request, recommended, alternatives)
        fallback_info = {
            "retry_cost": fb.retry_cost,
            "fallback_provider": fb.fallback_provider,
            "fallback_cost": fb.fallback_cost,
            "total_worst_case": fb.total_worst_case,
            "explanation": fb.explanation,
        }

    # margin simulation (ECO-FR-032, ECO-FR-033)
    margin_info = None
    if recommended and request.markup_mode:
        me = MarginEngine()
        mr = me.calculate(
            recommended,
            request.markup_mode,
            request.price_to_customer,
            request.target_margin_percent,
        )
        margin_info = {
            "markup_mode": mr.markup_mode,
            "price_to_customer": mr.price_to_customer,
            "gross_margin_amount": mr.gross_margin_amount,
            "gross_margin_percent": mr.gross_margin_percent,
            "is_margin_blocked": mr.is_margin_blocked,
            "explanation": mr.explanation,
        }
        # if margin blocked, override recommendation
        if mr.is_margin_blocked:
            recommended = None

    req_status = "blocked" if recommended is None else "completed"
    blocked_reason = None
    if recommended is None:
        if margin_info and margin_info.get("is_margin_blocked"):
            blocked_reason = margin_info["explanation"]
        else:
            blocked_reason = (
                "All routes exceeded the configured budget policy. "
                "Consider raising the budget cap or switching to async_ok."
            )

    request_id = request.request_id or str(uuid.uuid4())

    db_request = EconomicsRequest(
        id=request_id,
        request_payload=request.model_dump(mode="json"),
        status=req_status,
        recommended_route=recommended.provider if recommended else None,
        simulation_mode=request.simulation_mode,
    )
    db.add(db_request)

    for ranked_route in ranked:
        r = ranked_route.route
        db_decision = EconomicsDecision(
            economics_request_id=request_id,
            provider_key=r.provider,
            estimated_low_cost=r.estimated_low_cost,
            estimated_high_cost=r.estimated_high_cost,
            estimated_base_cost=r.estimated_base_cost,
            budget_status=r.budget_status,
            cost_class=r.cost_class,
            confidence_class=r.confidence_class,
            final_score=r.final_score,
            is_recommended=(recommended is not None and r.provider == recommended.provider),
            explanation=r.explanation,
        )
        db.add(db_decision)

    db.commit()

    # analytics events
    analytics = AnalyticsService(db)

    if recommended:
        analytics.track_estimate_created(
            request_id=request_id,
            use_case=request.use_case.value,
            provider=recommended.provider,
            estimated_base_cost=recommended.estimated_base_cost,
            budget_status=recommended.budget_status,
        )
        # async savings event
        async_routes = [r for r in all_routes if r.is_async_batch]
        sync_routes  = [r for r in all_routes if not r.is_async_batch]
        if async_routes and sync_routes:
            cheapest_sync  = min(sync_routes,  key=lambda r: r.estimated_base_cost)
            cheapest_async = min(async_routes, key=lambda r: r.estimated_base_cost)
            savings = cheapest_sync.estimated_base_cost - cheapest_async.estimated_base_cost
            if savings > 0:
                analytics.track_async_savings(request_id, cheapest_async.provider, round(savings, 4))

    # track blocked routes
    effective_cap = request.job_budget_cap or request.workspace_budget_cap
    for r in all_routes:
        if r.budget_status == "blocked" and effective_cap:
            analytics.track_budget_blocked(
                request_id, r.provider, r.estimated_high_cost, effective_cap
            )

    response = EconomicsResponseOut(
        request_id=request_id,
        recommended_route=recommended,
        alternatives=alternatives,
        all_routes=all_routes,
        request_status=req_status,
        blocked_reason=blocked_reason,
        simulation_mode=request.simulation_mode,
    )

    return {
        "response": response,
        "savings_delta": savings_delta,
        "fallback_info": fallback_info,
        "margin_info": margin_info,
    }


@router.post("/estimate", status_code=status.HTTP_201_CREATED)
def create_estimate(request: EconomicsRequestIn, db: Session = Depends(get_db)):
    result = _run_economics_pipeline(request, db)
    resp = result["response"]
    # attach extra sprint 2 fields
    out = resp.model_dump()
    out["savings_delta_vs_next"] = result["savings_delta"]
    out["fallback_exposure"] = result["fallback_info"]
    out["margin_simulation"] = result["margin_info"]
    return out


@router.post("/simulate", status_code=status.HTTP_200_OK)
def simulate_estimate(request: EconomicsRequestIn, db: Session = Depends(get_db)):
    simulated = request.model_copy(update={"simulation_mode": True})
    result = _run_economics_pipeline(simulated, db)
    resp = result["response"]
    out = resp.model_dump()
    out["savings_delta_vs_next"] = result["savings_delta"]
    out["fallback_exposure"] = result["fallback_info"]
    out["margin_simulation"] = result["margin_info"]
    return out


@router.get("/estimate/{request_id}")
def get_estimate(request_id: str, db: Session = Depends(get_db)):
    db_request = db.query(EconomicsRequest).filter(
        EconomicsRequest.id == request_id
    ).first()

    if not db_request:
        raise HTTPException(status_code=404, detail=f"Estimate {request_id} not found.")

    decisions = db.query(EconomicsDecision).filter(
        EconomicsDecision.economics_request_id == request_id
    ).all()

    all_routes = [d.to_dict() for d in decisions]
    recommended = next((d for d in all_routes if d.get("is_recommended")), None)
    alternatives = [
        d for d in all_routes
        if not d.get("is_recommended") and d.get("budget_status") != "blocked"
    ][:2]

    def _to_route(d):
        return RouteEstimate(
            provider=d["provider"],
            estimated_base_cost=d["estimated_base_cost"],
            estimated_low_cost=d["estimated_low_cost"],
            estimated_high_cost=d["estimated_high_cost"],
            budget_status=d["budget_status"],
            cost_class=d["cost_class"],
            confidence_class=d["confidence_class"],
            final_score=d.get("final_score"),
            explanation=d.get("explanation", ""),
        )

    return EconomicsResponseOut(
        request_id=request_id,
        recommended_route=_to_route(recommended) if recommended else None,
        alternatives=[_to_route(a) for a in alternatives],
        all_routes=[_to_route(r) for r in all_routes],
        request_status=db_request.status,
        simulation_mode=db_request.simulation_mode,
    )


@router.post("/estimate/{request_id}/override", status_code=status.HTTP_201_CREATED)
def override_estimate(
    request_id: str,
    payload: OverrideRequestIn,
    db: Session = Depends(get_db),
):
    db_request = db.query(EconomicsRequest).filter(
        EconomicsRequest.id == request_id
    ).first()

    if not db_request:
        raise HTTPException(status_code=404, detail=f"Estimate {request_id} not found.")

    original_provider = db_request.recommended_route or "unknown"

    override = EconomicsOverride(
        economics_request_id=request_id,
        original_provider=original_provider,
        override_provider=payload.override_provider,
        override_reason=payload.override_reason,
    )
    db.add(override)
    db.commit()

    # track analytics
    analytics = AnalyticsService(db)
    analytics.track_override(request_id, original_provider, payload.override_provider)

    return OverrideResponseOut(
        request_id=request_id,
        original_provider=original_provider,
        override_provider=payload.override_provider,
        override_reason=payload.override_reason,
        stored=True,
    )


@router.get("/providers")
def list_providers(db: Session = Depends(get_db)):
    registry = PricingRegistryService(db)
    profiles = registry.get_all_active()
    return {
        "count": len(profiles),
        "providers": [
            {
                "provider_key": p["provider_key"],
                "pricing_unit": p.get("pricing_unit"),
                "version": p.get("version"),
                "is_active": p.get("is_active"),
            }
            for p in profiles
        ],
    }
