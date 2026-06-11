from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from schemas_v2.economics_v2_schema import BudgetReservationIn, BudgetSettleIn, BudgetReleaseIn
from services_v2.budget.budget_guardrail_service import BudgetGuardrailService
from services_v2.analytics.analytics_service_v2 import AnalyticsServiceV2

router = APIRouter(prefix="/api/economics/v2/budget", tags=["Budget v2"])

@router.post("/reserve", status_code=201)
def reserve(payload: BudgetReservationIn, db: Session = Depends(get_db)):
    result = BudgetGuardrailService().reserve(payload, db)
    AnalyticsServiceV2(db).reservation_created(payload.estimate_id, None, payload.workspace_id, result["reservation_id"], payload.reserved_amount)
    return result

@router.post("/{reservation_id}/settle")
def settle(reservation_id: str, payload: BudgetSettleIn, db: Session = Depends(get_db)):
    result = BudgetGuardrailService().settle(reservation_id, payload.actual_amount, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result

@router.post("/{reservation_id}/release")
def release(reservation_id: str, db: Session = Depends(get_db)):
    result = BudgetGuardrailService().release(reservation_id, db)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
