import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db.database import init_db, SessionLocal
from services.pricing_registry_service import PricingRegistryService
from services_v2.pricing.pricing_intelligence_service import PricingIntelligenceService

def main():
    print("=== Economics Engine v2 Seeder ===")
    init_db()
    db = SessionLocal()
    try:
        print("Seeding v1 pricing profiles...")
        c1 = PricingRegistryService.seed_from_json(db)
        print(f"v1: {c1} inserted.")
        print("Seeding v2 pricing profiles...")
        c2 = PricingIntelligenceService.seed_from_json(db)
        print(f"v2: {c2} inserted.")
    finally:
        db.close()
    print("Done.")

if __name__ == "__main__":
    main()
