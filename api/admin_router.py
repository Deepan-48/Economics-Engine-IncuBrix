"""
api/admin_router.py

Admin endpoints for pricing profile management.
ECO-FR-050 : edit pricing profiles and thresholds
ECO-FR-052 : version rollback support
ECO-FR-053 : manual override by authorized user
"""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from db.database import get_db
from models.pricing_profile import PricingProfile
from config import settings

router = APIRouter(prefix=f"{settings.api_prefix}/admin", tags=["Admin"])


# input schemas

class UpdateProfileIn(BaseModel):
    pricing_profile_json: dict
    reason: Optional[str] = None


class ThresholdUpdateIn(BaseModel):
    near_budget_threshold: Optional[float] = None
    async_savings_threshold: Optional[float] = None


# in-memory threshold store (good enough for MVP)
_thresholds = {
    "near_budget_threshold": settings.default_near_budget_threshold,
    "async_savings_threshold": settings.default_async_savings_threshold,
}


@router.get("/providers", summary="List all provider profiles including inactive")
def list_all_providers(db: Session = Depends(get_db)):
    profiles = db.query(PricingProfile).order_by(
        PricingProfile.provider_key,
        PricingProfile.version.desc()
    ).all()

    return {
        "count": len(profiles),
        "providers": [
            {
                "id": str(p.id),
                "provider_key": p.provider_key,
                "version": p.version,
                "is_active": p.is_active,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in profiles
        ]
    }


@router.patch(
    "/providers/{provider_key}",
    summary="Update a provider pricing profile — creates new version",
)
def update_provider_profile(
    provider_key: str,
    payload: UpdateProfileIn,
    db: Session = Depends(get_db),
):
    # ECO-FR-050: allow editing pricing profiles

    existing = db.query(PricingProfile).filter(
        PricingProfile.provider_key == provider_key,
        PricingProfile.is_active == True,
    ).first()

    if not existing:
        raise HTTPException(status_code=404, detail=f"Provider {provider_key} not found.")

    # deactivate current version
    existing.is_active = False
    existing.updated_at = datetime.utcnow()

    # create new version
    new_version = PricingProfile(
        provider_key=provider_key,
        pricing_profile_json={
            **existing.pricing_profile_json,
            **payload.pricing_profile_json,
            "provider_key": provider_key,
        },
        version=existing.version + 1,
        is_active=True,
    )
    db.add(new_version)
    db.commit()

    return {
        "provider_key": provider_key,
        "new_version": new_version.version,
        "previous_version": existing.version,
        "message": f"Profile updated. New version {new_version.version} is now active.",
    }


@router.post(
    "/providers/{provider_key}/rollback",
    summary="Roll back to previous pricing profile version — ECO-FR-052",
)
def rollback_provider_profile(
    provider_key: str,
    db: Session = Depends(get_db),
):
    # get all versions sorted newest first
    versions = db.query(PricingProfile).filter(
        PricingProfile.provider_key == provider_key
    ).order_by(PricingProfile.version.desc()).all()

    if len(versions) < 2:
        raise HTTPException(
            status_code=400,
            detail="No previous version to roll back to."
        )

    current = next((v for v in versions if v.is_active), None)
    if not current:
        raise HTTPException(status_code=404, detail="No active version found.")

    # find previous version
    previous = next((v for v in versions if v.version < current.version), None)
    if not previous:
        raise HTTPException(status_code=400, detail="No previous version found.")

    current.is_active = False
    current.updated_at = datetime.utcnow()
    previous.is_active = True
    previous.updated_at = datetime.utcnow()
    db.commit()

    return {
        "provider_key": provider_key,
        "rolled_back_from": current.version,
        "rolled_back_to": previous.version,
        "message": f"Rolled back to version {previous.version}.",
    }


@router.post(
    "/providers/{provider_key}/toggle",
    summary="Activate or deactivate a provider",
)
def toggle_provider(
    provider_key: str,
    db: Session = Depends(get_db),
):
    profile = db.query(PricingProfile).filter(
        PricingProfile.provider_key == provider_key,
    ).order_by(PricingProfile.version.desc()).first()

    if not profile:
        raise HTTPException(status_code=404, detail=f"Provider {provider_key} not found.")

    profile.is_active = not profile.is_active
    profile.updated_at = datetime.utcnow()
    db.commit()

    return {
        "provider_key": provider_key,
        "is_active": profile.is_active,
        "message": f"Provider {provider_key} is now {'active' if profile.is_active else 'inactive'}.",
    }


@router.get("/thresholds", summary="Get current policy thresholds")
def get_thresholds():
    return _thresholds


@router.patch("/thresholds", summary="Update policy thresholds")
def update_thresholds(payload: ThresholdUpdateIn):
    if payload.near_budget_threshold is not None:
        _thresholds["near_budget_threshold"] = payload.near_budget_threshold
    if payload.async_savings_threshold is not None:
        _thresholds["async_savings_threshold"] = payload.async_savings_threshold
    return {"updated": _thresholds}


@router.get("/analytics", summary="Get recent analytics events")
def get_analytics(
    limit: int = 50,
    event_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    from models.analytics_event import AnalyticsEvent

    query = db.query(AnalyticsEvent)
    if event_type:
        query = query.filter(AnalyticsEvent.event_type == event_type)

    events = query.order_by(AnalyticsEvent.created_at.desc()).limit(limit).all()

    return {
        "count": len(events),
        "events": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "request_id": e.request_id,
                "properties": e.properties,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ]
    }
