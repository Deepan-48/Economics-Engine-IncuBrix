from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from db.database import get_db
from models.pricing_profile import PricingProfile
from config import settings

router = APIRouter(prefix=f"{settings.api_prefix}/admin", tags=["Admin v1"])

class UpdateProfileIn(BaseModel):
    pricing_profile_json: dict
    reason: Optional[str] = None

class ThresholdUpdateIn(BaseModel):
    near_budget_threshold: Optional[float] = None
    async_savings_threshold: Optional[float] = None

_thresholds = {"near_budget_threshold": 0.85, "async_savings_threshold": 0.15}

@router.get("/providers")
def list_all_providers(db: Session = Depends(get_db)):
    profiles = db.query(PricingProfile).order_by(PricingProfile.provider_key, PricingProfile.version.desc()).all()
    return {"count": len(profiles), "providers": [{"id": str(p.id), "provider_key": p.provider_key, "version": p.version, "is_active": p.is_active} for p in profiles]}

@router.patch("/providers/{provider_key}")
def update_provider_profile(provider_key: str, payload: UpdateProfileIn, db: Session = Depends(get_db)):
    existing = db.query(PricingProfile).filter(PricingProfile.provider_key == provider_key, PricingProfile.is_active == True).first()
    if not existing: raise HTTPException(status_code=404, detail=f"Provider {provider_key} not found.")
    existing.is_active = False
    new_p = PricingProfile(provider_key=provider_key, pricing_profile_json={**existing.pricing_profile_json, **payload.pricing_profile_json, "provider_key": provider_key}, version=existing.version + 1, is_active=True)
    db.add(new_p)
    db.commit()
    return {"provider_key": provider_key, "new_version": new_p.version, "previous_version": existing.version}

@router.post("/providers/{provider_key}/rollback")
def rollback_provider(provider_key: str, db: Session = Depends(get_db)):
    versions = db.query(PricingProfile).filter(PricingProfile.provider_key == provider_key).order_by(PricingProfile.version.desc()).all()
    if len(versions) < 2: raise HTTPException(status_code=400, detail="No previous version to roll back to.")
    current = next((v for v in versions if v.is_active), None)
    if not current: raise HTTPException(status_code=404, detail="No active version found.")
    previous = next((v for v in versions if v.version < current.version), None)
    if not previous: raise HTTPException(status_code=400, detail="No previous version found.")
    current.is_active = False
    previous.is_active = True
    db.commit()
    return {"provider_key": provider_key, "rolled_back_from": current.version, "rolled_back_to": previous.version}

@router.post("/providers/{provider_key}/toggle")
def toggle_provider(provider_key: str, db: Session = Depends(get_db)):
    p = db.query(PricingProfile).filter(PricingProfile.provider_key == provider_key).order_by(PricingProfile.version.desc()).first()
    if not p: raise HTTPException(status_code=404, detail=f"Provider {provider_key} not found.")
    p.is_active = not p.is_active
    db.commit()
    return {"provider_key": provider_key, "is_active": p.is_active}

@router.get("/thresholds")
def get_thresholds(): return _thresholds

@router.patch("/thresholds")
def update_thresholds(payload: ThresholdUpdateIn):
    if payload.near_budget_threshold is not None: _thresholds["near_budget_threshold"] = payload.near_budget_threshold
    if payload.async_savings_threshold is not None: _thresholds["async_savings_threshold"] = payload.async_savings_threshold
    return {"updated": _thresholds}

@router.get("/analytics")
def get_analytics(limit: int = 50, event_type: Optional[str] = None, db: Session = Depends(get_db)):
    from models.analytics_event import AnalyticsEvent
    query = db.query(AnalyticsEvent)
    if event_type: query = query.filter(AnalyticsEvent.event_type == event_type)
    events = query.order_by(AnalyticsEvent.created_at.desc()).limit(limit).all()
    return {"count": len(events), "events": [{"id": str(e.id), "event_type": e.event_type, "request_id": e.request_id, "properties": e.properties, "created_at": e.created_at.isoformat()} for e in events]}
