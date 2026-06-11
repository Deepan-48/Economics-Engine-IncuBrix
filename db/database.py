from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Generator
from config import settings

connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, connect_args=connect_args, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from models.economics_request import EconomicsRequest
    from models.pricing_profile import PricingProfile
    from models.economics_decision import EconomicsDecision, EconomicsOverride
    from models.analytics_event import AnalyticsEvent
    from models_v2.models_v2 import (
        PricingProfileV2, EconomicsEstimateV2, BudgetReservation,
        LedgerEntry, EconomicsScenario, ConfigVersion,
        ActualCostRecord, CostVarianceRecord, EconomicsAlert, EconomicsEventV2
    )
    Base.metadata.create_all(bind=engine)
