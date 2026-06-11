from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from db.database import get_db
from schemas_v2.economics_v2_schema import ActualCostImportIn
from services_v2.actuals.actuals_service import ActualsService

router = APIRouter(prefix="/api/economics/v2/actuals", tags=["Actuals v2"])

@router.post("/import", status_code=201)
def import_actual(payload: ActualCostImportIn, db: Session = Depends(get_db)):
    return ActualsService().import_actual(payload, db)

@router.get("/variance")
def variance_report(workspace_id: Optional[str] = None, provider_key: Optional[str] = None,
                    db: Session = Depends(get_db)):
    return ActualsService().get_variance_report(workspace_id, provider_key, db)

@router.get("/unmapped")
def unmapped(db: Session = Depends(get_db)):
    return {"unmapped": ActualsService().get_unmapped(db)}
