"""
services_v2/pricing/pricing_intelligence_service.py
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from models_v2.models_v2 import PricingProfileV2, ConfigVersion

SEED_FILE = Path(__file__).parent.parent.parent / "data_v2" / "pricing_profiles_v2.json"


class PricingIntelligenceService:

    def __init__(self, db: Session):
        self.db = db

    def get_active_profiles(self) -> list[dict]:
        profiles = (
            self.db.query(PricingProfileV2)
            .filter(
                PricingProfileV2.is_active == True,
                PricingProfileV2.approval_status == "active",
            )
            .order_by(PricingProfileV2.provider_key)
            .all()
        )
        return [p.to_dict() for p in profiles]

    def get_profile(self, provider_key: str) -> Optional[dict]:
        profile = (
            self.db.query(PricingProfileV2)
            .filter(
                PricingProfileV2.provider_key == provider_key,
                PricingProfileV2.is_active == True,
                PricingProfileV2.approval_status == "active",
            )
            .order_by(PricingProfileV2.profile_version.desc())
            .first()
        )
        return profile.to_dict() if profile else None

    def get_all_with_history(self) -> list[dict]:
        profiles = (
            self.db.query(PricingProfileV2)
            .order_by(PricingProfileV2.provider_key, PricingProfileV2.profile_version.desc())
            .all()
        )
        return [p.to_dict() for p in profiles]

    def stage_profile(self, provider_key: str, draft: dict, created_by: str = "admin") -> dict:
        latest = (
            self.db.query(PricingProfileV2)
            .filter(PricingProfileV2.provider_key == provider_key)
            .order_by(PricingProfileV2.profile_version.desc())
            .first()
        )
        new_version = (latest.profile_version + 1) if latest else 1

        staged = PricingProfileV2(
            provider_key=provider_key,
            model_key=draft.get("model_key", "default"),
            profile_version=new_version,
            environment=draft.get("environment", "production"),
            source_type=draft.get("source_type", "manual"),
            approval_status="staged",
            currency=draft.get("currency", "USD"),
            profile_data=draft,
            rate_cards=draft.get("rate_cards", []),
            modifiers=draft.get("modifiers", []),
            is_active=False,
        )
        self.db.add(staged)

        cfg = ConfigVersion(
            provider_key=provider_key,
            version_number=new_version,
            approval_status="staged",
            draft_profile=draft,
            created_by=created_by,
        )
        self.db.add(cfg)
        self.db.commit()

        return {
            "provider_key":    provider_key,
            "staged_version":  new_version,
            "approval_status": "staged",
            "message":         f"Version {new_version} staged. Validate then approve to activate.",
        }

    def validate_profile(self, provider_key: str, draft: dict) -> dict:
        errors = []
        warnings = []

        if not draft.get("rate_cards"):
            errors.append("rate_cards is required and must not be empty.")

        for rc in draft.get("rate_cards", []):
            if not rc.get("unit_type"):
                errors.append(f"rate_card missing unit_type: {rc}")
            if rc.get("unit_rate", 0) <= 0:
                errors.append(f"unit_rate must be > 0: {rc}")

        if not draft.get("default_uncertainty_multiplier_low"):
            warnings.append("default_uncertainty_multiplier_low not set, will use 0.9")
        if not draft.get("default_uncertainty_multiplier_high"):
            warnings.append("default_uncertainty_multiplier_high not set, will use 1.2")

        # update config_version record with result
        cfg = (
            self.db.query(ConfigVersion)
            .filter(
                ConfigVersion.provider_key == provider_key,
                ConfigVersion.approval_status == "staged",
            )
            .order_by(ConfigVersion.version_number.desc())
            .first()
        )
        result = {
            "valid":    len(errors) == 0,
            "errors":   errors,
            "warnings": warnings,
        }
        if cfg:
            cfg.validation_result = result
            self.db.commit()

        return result

    def approve_and_activate(self, provider_key: str, version: int, approved_by: str = "admin") -> dict:
        staged = (
            self.db.query(PricingProfileV2)
            .filter(
                PricingProfileV2.provider_key == provider_key,
                PricingProfileV2.profile_version == version,
                PricingProfileV2.approval_status == "staged",
            )
            .first()
        )
        if not staged:
            return {"error": f"No staged version {version} for {provider_key}"}

        current = (
            self.db.query(PricingProfileV2)
            .filter(
                PricingProfileV2.provider_key == provider_key,
                PricingProfileV2.is_active == True,
                PricingProfileV2.approval_status == "active",
            )
            .first()
        )
        if current:
            current.is_active = False
            current.approval_status = "inactive"
            current.updated_at = datetime.utcnow()

        staged.approval_status = "active"
        staged.is_active = True
        staged.updated_at = datetime.utcnow()

        cfg = (
            self.db.query(ConfigVersion)
            .filter(
                ConfigVersion.provider_key == provider_key,
                ConfigVersion.version_number == version,
            )
            .first()
        )
        if cfg:
            cfg.approval_status = "approved"
            cfg.approved_by = approved_by
            cfg.activated_at = datetime.utcnow()

        self.db.commit()
        return {
            "provider_key":      provider_key,
            "activated_version": version,
            "approved_by":       approved_by,
        }

    def rollback(self, provider_key: str) -> dict:
        versions = (
            self.db.query(PricingProfileV2)
            .filter(PricingProfileV2.provider_key == provider_key)
            .order_by(PricingProfileV2.profile_version.desc())
            .all()
        )
        if len(versions) < 2:
            return {"error": "No previous version to roll back to."}

        current = next((v for v in versions if v.is_active), None)
        if not current:
            return {"error": "No active version found."}

        previous = next(
            (v for v in versions if v.profile_version < current.profile_version), None
        )
        if not previous:
            return {"error": "No previous version found."}

        current.is_active = False
        current.approval_status = "rolled_back"
        current.updated_at = datetime.utcnow()
        previous.is_active = True
        previous.approval_status = "active"
        previous.updated_at = datetime.utcnow()

        self.db.commit()
        return {
            "provider_key":      provider_key,
            "rolled_back_from":  current.profile_version,
            "rolled_back_to":    previous.profile_version,
        }

    def get_impact_preview(self, provider_key: str, version: int) -> dict:
        staged = (
            self.db.query(PricingProfileV2)
            .filter(
                PricingProfileV2.provider_key == provider_key,
                PricingProfileV2.profile_version == version,
            )
            .first()
        )
        current = (
            self.db.query(PricingProfileV2)
            .filter(
                PricingProfileV2.provider_key == provider_key,
                PricingProfileV2.is_active == True,
            )
            .first()
        )
        if not staged:
            return {"error": "Staged version not found."}

        current_rate = 0
        staged_rate = 0
        if current and current.rate_cards:
            current_rate = current.rate_cards[0].get("unit_rate", 0)
        if staged.rate_cards:
            staged_rate = staged.rate_cards[0].get("unit_rate", 0)

        delta = round(staged_rate - current_rate, 6)
        return {
            "provider_key":    provider_key,
            "current_version": current.profile_version if current else None,
            "staged_version":  version,
            "rate_delta":      delta,
            "cost_impact":     "higher" if delta > 0 else "lower" if delta < 0 else "same",
            "message":         f"New rate is {'higher' if delta > 0 else 'lower' if delta < 0 else 'same'} by {abs(delta):.6f} per unit.",
        }

    @staticmethod
    def seed_from_json(db: Session, json_path: Path = SEED_FILE) -> int:
        with open(json_path) as f:
            profiles = json.load(f)

        inserted = 0
        for p in profiles:
            provider_key = p["provider_key"]
            existing = db.query(PricingProfileV2).filter(
                PricingProfileV2.provider_key == provider_key,
                PricingProfileV2.is_active == True,
            ).first()
            if existing:
                print(f"  [skip] {provider_key} already seeded v{existing.profile_version}")
                continue

            obj = PricingProfileV2(
                provider_key=provider_key,
                model_key=p.get("model_key", "default"),
                profile_version=p.get("profile_version", 1),
                environment=p.get("environment", "production"),
                source_type=p.get("source_type", "manual"),
                approval_status="active",
                currency=p.get("currency", "USD"),
                profile_data=p,
                rate_cards=p.get("rate_cards", []),
                modifiers=p.get("modifiers", []),
                is_active=True,
            )
            db.add(obj)
            inserted += 1
            print(f"  [seed] {provider_key} v{obj.profile_version}")

        db.commit()
        return inserted
