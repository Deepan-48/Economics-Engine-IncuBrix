"""
scripts/seed_pricing_data.py

Seeds the pricing_profiles table with all 5 mock provider profiles
from data/pricing_registry.json.

Run once after DB is created:
    python scripts/seed_pricing_data.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.database import init_db, SessionLocal
from services.pricing_registry_service import PricingRegistryService


def main():
    print("=== Economics Engine — Pricing Data Seeder ===")
    print("Initialising database tables...")
    init_db()

    db = SessionLocal()
    try:
        print("Seeding provider pricing profiles...")
        count = PricingRegistryService.seed_from_json(db)
        if count == 0:
            print("All providers already seeded. Nothing to do.")
        else:
            print(f"Done. {count} provider profile(s) inserted.")
    finally:
        db.close()

    print("==============================================")


if __name__ == "__main__":
    main()
