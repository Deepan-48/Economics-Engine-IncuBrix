"""
services_v2/ledger/ledger_service.py
ECO2-LED-001 to ECO2-LED-004
"""
from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import func
from models_v2.models_v2 import LedgerEntry
from schemas_v2.economics_v2_schema import LedgerEntryIn


class LedgerService:

    def add_entry(self, payload: LedgerEntryIn, db: Session) -> dict:
        entry = LedgerEntry(
            workspace_id=payload.workspace_id,
            project_id=payload.project_id,
            campaign_id=payload.campaign_id,
            job_id=payload.job_id,
            provider_key=payload.provider_key,
            use_case=payload.use_case,
            entry_type=payload.entry_type.value,
            amount=payload.amount,
            currency=payload.currency,
            source_ref=payload.source_ref,
            notes=payload.notes,
        )
        db.add(entry)
        db.commit()
        return {"id": str(entry.id), "entry_type": entry.entry_type,
                "amount": float(entry.amount), "currency": entry.currency}

    def get_summary(self, workspace_id: str = None, campaign_id: str = None,
                    provider_key: str = None, db: Session = None) -> dict:
        query = db.query(
            LedgerEntry.entry_type,
            func.sum(LedgerEntry.amount).label("total"),
            LedgerEntry.currency,
        )
        if workspace_id:
            query = query.filter(LedgerEntry.workspace_id == workspace_id)
        if campaign_id:
            query = query.filter(LedgerEntry.campaign_id == campaign_id)
        if provider_key:
            query = query.filter(LedgerEntry.provider_key == provider_key)

        rows = query.group_by(LedgerEntry.entry_type, LedgerEntry.currency).all()
        summary = {}
        for row in rows:
            summary[row.entry_type] = round(float(row.total), 4)

        estimated  = summary.get("estimated", 0)
        actual     = summary.get("actual", 0)
        reserved   = summary.get("reserved", 0)
        released   = summary.get("released", 0)

        return {
            "workspace_id": workspace_id,
            "campaign_id":  campaign_id,
            "provider_key": provider_key,
            "by_type":      summary,
            "total_estimated": estimated,
            "total_actual":    actual,
            "total_reserved":  reserved,
            "total_released":  released,
            "variance":        round(actual - estimated, 4) if actual and estimated else None,
        }

    def get_entries(self, workspace_id: str = None, entry_type: str = None,
                    limit: int = 100, db: Session = None) -> list[dict]:
        query = db.query(LedgerEntry)
        if workspace_id:
            query = query.filter(LedgerEntry.workspace_id == workspace_id)
        if entry_type:
            query = query.filter(LedgerEntry.entry_type == entry_type)
        rows = query.order_by(LedgerEntry.created_at.desc()).limit(limit).all()
        return [
            {"id": str(r.id), "entry_type": r.entry_type, "amount": float(r.amount),
             "currency": r.currency, "provider_key": r.provider_key,
             "workspace_id": r.workspace_id, "campaign_id": r.campaign_id,
             "source_ref": r.source_ref, "notes": r.notes,
             "created_at": r.created_at.isoformat()}
            for r in rows
        ]
