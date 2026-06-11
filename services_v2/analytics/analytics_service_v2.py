"""
services_v2/analytics/analytics_service_v2.py
ECO2-ANA-001 to ECO2-ANA-004
"""
from __future__ import annotations
import csv, io, json
from sqlalchemy.orm import Session
from sqlalchemy import func
from models_v2.models_v2 import EconomicsEventV2, LedgerEntry, EconomicsEstimateV2

SCHEMA_VERSION = "v2.0"


class AnalyticsServiceV2:

    def __init__(self, db: Session):
        self.db = db

    def publish(self, event_type: str, request_id: str = None, correlation_id: str = None,
                workspace_id: str = None, properties: dict = None):
        e = EconomicsEventV2(
            event_type=event_type, schema_version=SCHEMA_VERSION,
            correlation_id=correlation_id, request_id=request_id,
            workspace_id=workspace_id, properties=properties or {},
        )
        self.db.add(e)
        try:
            self.db.commit()
        except Exception as ex:
            self.db.rollback()
            print(f"[AnalyticsV2] failed {event_type}: {ex}")

    def estimate_created(self, req_id, corr_id, ws_id, provider, base_cost, budget_status):
        self.publish("economics.v2.estimate.created", req_id, corr_id, ws_id,
                     {"provider": provider, "estimated_base_cost": base_cost, "budget_status": budget_status})

    def budget_blocked(self, req_id, corr_id, ws_id, provider, high_cost, cap):
        self.publish("economics.v2.budget.blocked", req_id, corr_id, ws_id,
                     {"provider": provider, "estimated_high_cost": high_cost, "cap": cap})

    def reservation_created(self, req_id, corr_id, ws_id, reservation_id, amount):
        self.publish("economics.v2.budget.reserved", req_id, corr_id, ws_id,
                     {"reservation_id": reservation_id, "reserved_amount": amount})

    def override_submitted(self, req_id, corr_id, ws_id, original, override, reason):
        self.publish("economics.v2.decision.overridden", req_id, corr_id, ws_id,
                     {"original_provider": original, "override_provider": override, "reason": reason})

    def profile_activated(self, provider_key, version, approved_by):
        self.publish("economics.v2.config.profile.activated", provider_key, None, None,
                     {"provider_key": provider_key, "version": version, "approved_by": approved_by})

    def batch_savings_recommended(self, req_id, corr_id, ws_id, provider, savings, pct):
        self.publish("economics.v2.batch.savings_recommended", req_id, corr_id, ws_id,
                     {"provider": provider, "estimated_savings": savings, "savings_percent": pct})

    def actual_imported(self, actual_cost_id, provider_key, amount, map_status):
        self.publish("economics.v2.actual.imported", actual_cost_id, None, None,
                     {"actual_cost_id": actual_cost_id, "provider_key": provider_key,
                      "amount": amount, "mapped_status": map_status})

    def variance_detected(self, estimate_id, variance_pct, severity):
        self.publish("economics.v2.variance.detected", estimate_id, None, None,
                     {"estimate_id": estimate_id, "variance_percent": variance_pct, "severity": severity})

    def get_summary(self, workspace_id: str = None) -> dict:
        q_estimates = self.db.query(
            func.count(EconomicsEstimateV2.id).label("total_estimates"),
            func.sum(EconomicsEstimateV2.estimated_base_cost).label("total_estimated"),
        )
        if workspace_id:
            q_estimates = q_estimates.filter(EconomicsEstimateV2.workspace_id == workspace_id)
        est_row = q_estimates.first()

        q_blocked = self.db.query(func.count(EconomicsEstimateV2.id)).filter(
            EconomicsEstimateV2.budget_status == "blocked_hard_cap"
        )
        blocked_count = q_blocked.scalar() or 0

        q_actual = self.db.query(func.sum(LedgerEntry.amount)).filter(LedgerEntry.entry_type == "actual")
        if workspace_id:
            q_actual = q_actual.filter(LedgerEntry.workspace_id == workspace_id)
        total_actual = float(q_actual.scalar() or 0)

        total_est = float(est_row.total_estimated or 0)
        return {
            "workspace_id":     workspace_id,
            "total_estimates":  est_row.total_estimates or 0,
            "total_estimated":  round(total_est, 4),
            "total_actual":     round(total_actual, 4),
            "total_variance":   round(total_actual - total_est, 4),
            "blocked_count":    blocked_count,
        }

    def get_events(self, event_type: str = None, workspace_id: str = None,
                   limit: int = 50) -> list[dict]:
        query = self.db.query(EconomicsEventV2)
        if event_type:
            query = query.filter(EconomicsEventV2.event_type == event_type)
        if workspace_id:
            query = query.filter(EconomicsEventV2.workspace_id == workspace_id)
        rows = query.order_by(EconomicsEventV2.created_at.desc()).limit(limit).all()
        return [
            {"id": str(r.id), "event_type": r.event_type,
             "request_id": r.request_id, "workspace_id": r.workspace_id,
             "properties": r.properties, "created_at": r.created_at.isoformat()}
            for r in rows
        ]

    def export_csv(self, workspace_id: str = None) -> str:
        rows = self.get_events(workspace_id=workspace_id, limit=1000)
        if not rows:
            return ""
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["id", "event_type", "request_id", "workspace_id", "created_at"])
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in ["id", "event_type", "request_id", "workspace_id", "created_at"]})
        return output.getvalue()
