"""
api_v2/pricing_router.py
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from schemas_v2.economics_v2_schema import StageProfileIn, ConfigValidateIn
from services_v2.pricing.pricing_intelligence_service import PricingIntelligenceService
from services_v2.analytics.analytics_service_v2 import AnalyticsServiceV2

router = APIRouter(prefix="/api/economics/v2/providers", tags=["Pricing v2"])


@router.get("/pricing/active")
def list_active_profiles(db: Session = Depends(get_db)):
    svc = PricingIntelligenceService(db)
    profiles = svc.get_active_profiles()
    return {"count": len(profiles), "providers": profiles}


@router.get("/{provider_key}/pricing")
def get_provider_profile(provider_key: str, db: Session = Depends(get_db)):
    svc = PricingIntelligenceService(db)
    profile = svc.get_profile(provider_key)
    if not profile:
        raise HTTPException(status_code=404, detail=f"{provider_key} not found.")
    return profile


@router.get("/pricing/history")
def get_all_profiles_history(db: Session = Depends(get_db)):
    svc = PricingIntelligenceService(db)
    return {"profiles": svc.get_all_with_history()}


@router.post("/{provider_key}/pricing/stage", status_code=201)
def stage_profile(provider_key: str, payload: StageProfileIn, db: Session = Depends(get_db)):
    svc = PricingIntelligenceService(db)
    return svc.stage_profile(provider_key, payload.profile_data, payload.created_by)


@router.post("/{provider_key}/pricing/validate")
def validate_profile(provider_key: str, payload: ConfigValidateIn, db: Session = Depends(get_db)):
    svc = PricingIntelligenceService(db)
    return svc.validate_profile(provider_key, payload.draft_profile)


@router.post("/{provider_key}/pricing/approve")
def approve_profile(provider_key: str, version: int, approved_by: str = "admin", db: Session = Depends(get_db)):
    svc = PricingIntelligenceService(db)
    result = svc.approve_and_activate(provider_key, version, approved_by)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    AnalyticsServiceV2(db).profile_activated(provider_key, version, approved_by)
    return result


@router.post("/{provider_key}/pricing/rollback")
def rollback_profile(provider_key: str, db: Session = Depends(get_db)):
    svc = PricingIntelligenceService(db)
    result = svc.rollback(provider_key)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/{provider_key}/pricing/impact/{version}")
def impact_preview(provider_key: str, version: int, db: Session = Depends(get_db)):
    svc = PricingIntelligenceService(db)
    return svc.get_impact_preview(provider_key, version)
