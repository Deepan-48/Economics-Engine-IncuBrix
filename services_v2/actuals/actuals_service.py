"""
services_v2/actuals/actuals_service.py
ECO2-ACT-001 to ECO2-ACT-004
"""
from __future__ import annotations
from sqlalchemy.orm import Session
from models_v2.models_v2 import ActualCostRecord, CostVarianceRecord, EconomicsEstimateV2, LedgerEntry
from schemas_v2.economics_v2_schema import ActualCostImportIn

VARIANCE_THRESHOLD_HIGH     = 0.30
VARIANCE_THRESHOLD_CRITICAL = 0.50


def _severity(pct: float) -> str:
    if abs(pct) >= VARIANCE_THRESHOLD_CRITICAL * 100:
        return "critical"
    if abs(pct) >= VARIANCE_THRESHOLD_HIGH * 100:
        return "high"
    if abs(pct) >= 10:
        return "medium"
    return "low"


class ActualsService:

    def import_actual(self, payload: ActualCostImportIn, db: Session) -> dict:
        record = ActualCostRecord(
            provider_key=payload.provider_key,
            provider_job_id=payload.provider_job_id,
            provider_request_id=payload.provider_request_id,
            estimate_id=payload.estimate_id,
            job_id=payload.job_id,
            workspace_id=payload.workspace_id,
            actual_amount=payload.actual_amount,
            currency=payload.currency,
            billing_unit=payload.billing_unit,
            unit_quantity=payload.unit_quantity,
            import_source=payload.import_source,
            notes=payload.notes,
            map_status="unmapped",
        )
        db.add(record)

        if payload.estimate_id:
            estimate = db.query(EconomicsEstimateV2).filter(
                EconomicsEstimateV2.id == payload.estimate_id
            ).first()
            if estimate:
                record.map_status = "mapped"
                self._create_variance(record, estimate, db)

        db.add(LedgerEntry(
            workspace_id=payload.workspace_id,
            provider_key=payload.provider_key,
            entry_type="actual",
            amount=payload.actual_amount,
            currency=payload.currency,
            source_ref=str(record.id),
            notes="Actual cost imported",
        ))

        db.commit()
        return {
            "actual_cost_id": str(record.id),
            "map_status":     record.map_status,
            "provider_key":   record.provider_key,
            "actual_amount":  float(record.actual_amount),
            "message":        "Mapped to estimate." if record.map_status == "mapped" else "Added to unmapped queue.",
        }

    def _create_variance(self, actual: ActualCostRecord, estimate: EconomicsEstimateV2, db: Session):
        est_amount = float(estimate.estimated_base_cost)
        act_amount = float(actual.actual_amount)
        variance_amount = round(act_amount - est_amount, 4)
        variance_pct    = round((variance_amount / est_amount) * 100, 2) if est_amount > 0 else 0.0
        severity        = _severity(variance_pct)

        v = CostVarianceRecord(
            estimate_id=str(estimate.id),
            actual_cost_id=str(actual.id),
            provider_key=actual.provider_key,
            workspace_id=actual.workspace_id,
            estimated_amount=est_amount,
            actual_amount=act_amount,
            variance_amount=variance_amount,
            variance_percent=variance_pct,
            variance_reason="over_estimate" if variance_amount < 0 else "under_estimate",
            severity=severity,
        )
        db.add(v)

    def get_variance_report(self, workspace_id: str = None, provider_key: str = None,
                            db: Session = None) -> dict:
        query = db.query(CostVarianceRecord)
        if workspace_id:
            query = query.filter(CostVarianceRecord.workspace_id == workspace_id)
        if provider_key:
            query = query.filter(CostVarianceRecord.provider_key == provider_key)

        rows = query.order_by(CostVarianceRecord.created_at.desc()).limit(100).all()
        records = [
            {
                "estimate_id":      r.estimate_id,
                "provider_key":     r.provider_key,
                "estimated_amount": float(r.estimated_amount),
                "actual_amount":    float(r.actual_amount),
                "variance_amount":  float(r.variance_amount),
                "variance_percent": float(r.variance_percent),
                "variance_reason":  r.variance_reason,
                "severity":         r.severity,
                "created_at":       r.created_at.isoformat(),
            }
            for r in rows
        ]
        total_variance = sum(r["variance_amount"] for r in records)
        critical = [r for r in records if r["severity"] == "critical"]

        return {
            "total_records":   len(records),
            "total_variance":  round(total_variance, 4),
            "critical_count":  len(critical),
            "records":         records,
        }

    def get_unmapped(self, db: Session) -> list[dict]:
        rows = db.query(ActualCostRecord).filter(
            ActualCostRecord.map_status == "unmapped"
        ).order_by(ActualCostRecord.created_at.desc()).all()
        return [
            {"id": str(r.id), "provider_key": r.provider_key,
             "actual_amount": float(r.actual_amount), "currency": r.currency,
             "import_source": r.import_source, "created_at": r.created_at.isoformat()}
            for r in rows
        ]
