"""
services/pricing_registry_service.py

Loads provider pricing profiles from the database (seeded from JSON).
Provides lookup by provider key and filtering by active status.

Satisfies: ECO-FR-010, ECO-FR-011, ECO-FR-012, ECO-FR-013
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session

from models.pricing_profile import PricingProfile


# Path to seed data
REGISTRY_JSON = Path(__file__).parent.parent / "data" / "pricing_registry.json"


class PricingRegistryService:
    """
    Loads and serves provider pricing profiles.
    In MVP: reads from DB (pre-seeded from JSON).
    """

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_all_active(self) -> list[dict]:
        """Return all active provider pricing profiles as dicts."""
        profiles = (
            self.db.query(PricingProfile)
            .filter(PricingProfile.is_active == True)  # noqa: E712
            .order_by(PricingProfile.provider_key)
            .all()
        )
        return [p.to_dict() for p in profiles]

    def get_profile(self, provider_key: str) -> Optional[dict]:
        """Return the active pricing profile for a single provider, or None."""
        profile = (
            self.db.query(PricingProfile)
            .filter(
                PricingProfile.provider_key == provider_key,
                PricingProfile.is_active == True,  # noqa: E712
            )
            .order_by(PricingProfile.version.desc())
            .first()
        )
        return profile.to_dict() if profile else None

    def list_provider_keys(self) -> list[str]:
        """Return all active provider keys."""
        rows = (
            self.db.query(PricingProfile.provider_key)
            .filter(PricingProfile.is_active == True)  # noqa: E712
            .distinct()
            .all()
        )
        return [r[0] for r in rows]

    # ------------------------------------------------------------------
    # Seed helper (called by seed script, not normally at request time)
    # ------------------------------------------------------------------

    @staticmethod
    def seed_from_json(db: Session, json_path: Path = REGISTRY_JSON) -> int:
        """
        Insert provider profiles from JSON file into DB.
        Skips providers that already have an active version.
        Returns count of inserted rows.
        """
        with open(json_path, "r") as f:
            profiles: list[dict] = json.load(f)

        inserted = 0
        for p in profiles:
            provider_key = p["provider_key"]
            existing = (
                db.query(PricingProfile)
                .filter(
                    PricingProfile.provider_key == provider_key,
                    PricingProfile.is_active == True,  # noqa: E712
                )
                .first()
            )
            if existing:
                print(f"  [skip] {provider_key} already seeded (v{existing.version})")
                continue

            profile_obj = PricingProfile(
                provider_key=provider_key,
                pricing_profile_json=p,
                version=p.get("cost_model_version", 1),
                is_active=True,
            )
            db.add(profile_obj)
            inserted += 1
            print(f"  [seed] {provider_key} v{profile_obj.version}")

        db.commit()
        return inserted
