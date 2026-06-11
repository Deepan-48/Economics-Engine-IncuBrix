from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from typing import Optional
from db.database import get_db
from services_v2.analytics.analytics_service_v2 import AnalyticsServiceV2
from services_v2.forecasting.forecasting_service import ForecastingService

router = APIRouter(prefix="/api/economics/v2/analytics", tags=["Analytics v2"])

@router.get("/summary")
def summary(workspace_id: Optional[str] = None, db: Session = Depends(get_db)):
    return AnalyticsServiceV2(db).get_summary(workspace_id)

@router.get("/events")
def events(event_type: Optional[str] = None, workspace_id: Optional[str] = None,
           limit: int = 50, db: Session = Depends(get_db)):
    return {"events": AnalyticsServiceV2(db).get_events(event_type, workspace_id, limit)}

@router.get("/export/csv", response_class=PlainTextResponse)
def export_csv(workspace_id: Optional[str] = None, db: Session = Depends(get_db)):
    return AnalyticsServiceV2(db).export_csv(workspace_id)

@router.get("/forecast")
def forecast(workspace_id: Optional[str] = None, days_ahead: int = 30,
             monthly_budget: Optional[float] = None, db: Session = Depends(get_db)):
    return ForecastingService().forecast_spend(workspace_id, days_ahead, monthly_budget, db)

@router.get("/anomalies")
def anomalies(workspace_id: Optional[str] = None, db: Session = Depends(get_db)):
    return {"anomalies": ForecastingService().detect_anomalies(workspace_id, db)}

@router.get("/alerts")
def alerts(workspace_id: Optional[str] = None, is_resolved: bool = False, db: Session = Depends(get_db)):
    return {"alerts": ForecastingService().get_alerts(workspace_id, is_resolved, db)}
