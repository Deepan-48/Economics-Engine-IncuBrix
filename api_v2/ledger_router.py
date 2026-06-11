from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from db.database import get_db
from schemas_v2.economics_v2_schema import LedgerEntryIn
from services_v2.ledger.ledger_service import LedgerService

router = APIRouter(prefix="/api/economics/v2/ledger", tags=["Ledger v2"])

@router.post("/entries", status_code=201)
def add_entry(payload: LedgerEntryIn, db: Session = Depends(get_db)):
    return LedgerService().add_entry(payload, db)

@router.get("/summary")
def get_summary(workspace_id: Optional[str] = None, campaign_id: Optional[str] = None,
                provider_key: Optional[str] = None, db: Session = Depends(get_db)):
    return LedgerService().get_summary(workspace_id, campaign_id, provider_key, db)

@router.get("/entries")
def get_entries(workspace_id: Optional[str] = None, entry_type: Optional[str] = None,
                limit: int = 100, db: Session = Depends(get_db)):
    return {"entries": LedgerService().get_entries(workspace_id, entry_type, limit, db)}
