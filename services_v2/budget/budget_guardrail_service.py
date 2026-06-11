"""
services_v2/budget/budget_guardrail_service.py

ECO2-BUD-001 to ECO2-BUD-005
"""

from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from models_v2.models_v2 import BudgetReservation, LedgerEntry
from schemas_v2.economics_v2_schema import EstimateResultV2, BudgetReservationIn

NEAR_CAP_THRESHOLD = 0.85


class BudgetGuardrailService:

    def check(
        self,
        estimate: EstimateResultV2,
        job_budget_cap: Optional[float] = None,
        workspace_budget_cap: Optional[float] = None,
        campaign_budget_cap: Optional[float] = None,
    ) -> dict:
        cap = job_budget_cap or workspace_budget_cap or campaign_budget_cap
        high = estimate.estimated_high_cost

        if cap is None:
            return {"budget_status": "safe", "remaining_budget": None, "blocked_reason": None, "warning_reason": None}

        remaining = round(cap - high, 4)

        if high > cap:
            return {
                "budget_status":  "blocked_hard_cap",
                "remaining_budget": remaining,
                "blocked_reason": (
                    f"High cost ${high:.2f} exceeds cap ${cap:.2f}. "
                    f"Try: reduce batch size, use async_ok, lower quality bar."
                ),
                "warning_reason": None,
            }

        if high >= cap * NEAR_CAP_THRESHOLD:
            return {
                "budget_status":  "warn_near_cap",
                "remaining_budget": remaining,
                "blocked_reason": None,
                "warning_reason": f"Est. ${high:.2f} is within {round((1 - NEAR_CAP_THRESHOLD)*100)}% of cap ${cap:.2f}.",
            }

        return {"budget_status": "safe", "remaining_budget": remaining, "blocked_reason": None, "warning_reason": None}

    def reserve(self, payload: BudgetReservationIn, db: Session) -> dict:
        expires_at = datetime.utcnow() + timedelta(minutes=payload.expires_minutes)

        r = BudgetReservation(
            estimate_id=payload.estimate_id,
            workspace_id=payload.workspace_id,
            campaign_id=payload.campaign_id,
            scope_type=payload.scope_type,
            scope_id=payload.scope_id,
            reserved_amount=payload.reserved_amount,
            currency=payload.currency,
            status="reserved",
            expires_at=expires_at,
        )
        db.add(r)

        db.add(LedgerEntry(
            workspace_id=payload.workspace_id,
            campaign_id=payload.campaign_id,
            entry_type="reserved",
            amount=payload.reserved_amount,
            currency=payload.currency,
            source_ref=str(r.id),
            notes=f"Reserved for estimate {payload.estimate_id}",
        ))
        db.commit()

        return {
            "reservation_id":  str(r.id),
            "estimate_id":     payload.estimate_id,
            "workspace_id":    payload.workspace_id,
            "scope_type":      payload.scope_type,
            "reserved_amount": float(r.reserved_amount),
            "currency":        r.currency,
            "status":          r.status,
            "expires_at":      expires_at.isoformat(),
        }

    def settle(self, reservation_id: str, actual_amount: float, db: Session) -> dict:
        r = db.query(BudgetReservation).filter(BudgetReservation.id == reservation_id).first()
        if not r:
            return {"error": f"Reservation {reservation_id} not found."}

        reserved  = float(r.reserved_amount)
        released  = round(max(0.0, reserved - actual_amount), 4)

        r.status = "settled"
        r.settled_amount = actual_amount
        r.released_amount = released
        r.updated_at = datetime.utcnow()

        db.add(LedgerEntry(
            workspace_id=r.workspace_id, campaign_id=r.campaign_id,
            entry_type="actual", amount=actual_amount, currency=r.currency,
            source_ref=reservation_id, notes="Actual cost settled",
        ))
        if released > 0:
            db.add(LedgerEntry(
                workspace_id=r.workspace_id, campaign_id=r.campaign_id,
                entry_type="released", amount=released, currency=r.currency,
                source_ref=reservation_id, notes="Unused budget released",
            ))
        db.commit()

        return {"reservation_id": reservation_id, "status": "settled", "actual_amount": actual_amount, "released_amount": released}

    def release(self, reservation_id: str, db: Session) -> dict:
        r = db.query(BudgetReservation).filter(BudgetReservation.id == reservation_id).first()
        if not r:
            return {"error": f"Reservation {reservation_id} not found."}

        released = float(r.reserved_amount)
        r.status = "released"
        r.released_amount = released
        r.updated_at = datetime.utcnow()

        db.add(LedgerEntry(
            workspace_id=r.workspace_id, campaign_id=r.campaign_id,
            entry_type="released", amount=released, currency=r.currency,
            source_ref=reservation_id, notes="Reservation released",
        ))
        db.commit()

        return {"reservation_id": reservation_id, "status": "released", "released_amount": released}
