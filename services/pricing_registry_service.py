from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from sqlalchemy.orm import Session
from models.pricing_profile import PricingProfile

REGISTRY_JSON = Path(__file__).parent.parent / "data" / "pricing_registry.json"

class PricingRegistryService:
    def __init__(self, db: Session):
        self.db = db

    def get_all_active(self):
        profiles = self.db.query(PricingProfile).filter(PricingProfile.is_active == True).all()
        return [p.to_dict() for p in profiles]

    def get_profile(self, provider_key):
        p = self.db.query(PricingProfile).filter(
            PricingProfile.provider_key == provider_key, PricingProfile.is_active == True
        ).order_by(PricingProfile.version.desc()).first()
        return p.to_dict() if p else None

    def list_provider_keys(self):
        rows = self.db.query(PricingProfile.provider_key).filter(PricingProfile.is_active == True).distinct().all()
        return [r[0] for r in rows]

    @staticmethod
    def seed_from_json(db, json_path=REGISTRY_JSON):
        with open(json_path) as f:
            profiles = json.load(f)
        inserted = 0
        for p in profiles:
            pk = p["provider_key"]
            existing = db.query(PricingProfile).filter(PricingProfile.provider_key == pk, PricingProfile.is_active == True).first()
            if existing:
                print(f"  [skip] {pk}")
                continue
            obj = PricingProfile(provider_key=pk, pricing_profile_json=p, version=p.get("cost_model_version", 1), is_active=True)
            db.add(obj)
            inserted += 1
            print(f"  [seed] {pk}")
        db.commit()
        return inserted
