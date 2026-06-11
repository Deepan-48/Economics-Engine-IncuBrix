"""
services_v2/forecasting/forecasting_service.py
ECO2-FOR-001 to ECO2-FOR-004
"""
from __future__ import annotations
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from models_v2.models_v2 import LedgerEntry, EconomicsAlert


class ForecastingService:

    def forecast_spend(self, workspace_id: str = None, days_ahead: int = 30,
                       monthly_budget: float = None, db: Session = None) -> dict:
        cutoff = datetime.utcnow() - timedelta(days=30)
        query = db.query(func.sum(LedgerEntry.amount)).filter(
            LedgerEntry.entry_type == "actual",
            LedgerEntry.created_at >= cutoff,
        )
        if workspace_id:
            query = query.filter(LedgerEntry.workspace_id == workspace_id)

        actual_30d = float(query.scalar() or 0)
        daily_avg  = actual_30d / 30 if actual_30d > 0 else 0
        forecasted = round(daily_avg * days_ahead, 4)

        runway_warning = None
        projected_breach_date = None
        if monthly_budget and daily_avg > 0:
            days_to_breach = monthly_budget / daily_avg
            if days_to_breach < days_ahead:
                breach_date = datetime.utcnow() + timedelta(days=days_to_breach)
                projected_breach_date = breach_date.isoformat()
                runway_warning = f"At current rate, budget of ${monthly_budget:.2f} will be exhausted by {breach_date.strftime('%Y-%m-%d')}."
                self._create_alert(
                    db, "budget_runway_warning", "high", workspace_id,
                    "Budget runway warning",
                    runway_warning,
                    {"daily_avg": daily_avg, "projected_breach_date": projected_breach_date},
                )

        return {
            "workspace_id":          workspace_id,
            "actual_spend_last_30d": actual_30d,
            "daily_average":         round(daily_avg, 4),
            "forecasted_spend":      forecasted,
            "forecast_days":         days_ahead,
            "monthly_budget":        monthly_budget,
            "runway_warning":        runway_warning,
            "projected_breach_date": projected_breach_date,
        }

    def detect_anomalies(self, workspace_id: str = None, db: Session = None) -> list[dict]:
        from models_v2.models_v2 import CostVarianceRecord
        rows = db.query(CostVarianceRecord).filter(
            CostVarianceRecord.severity.in_(["high", "critical"])
        )
        if workspace_id:
            rows = rows.filter(CostVarianceRecord.workspace_id == workspace_id)
        rows = rows.order_by(CostVarianceRecord.created_at.desc()).limit(20).all()

        alerts = []
        for r in rows:
            self._create_alert(
                db, "cost_anomaly", r.severity, workspace_id,
                f"Cost anomaly: {r.provider_key}",
                f"Variance {r.variance_percent:.1f}% for estimate {r.estimate_id}.",
                {"variance_percent": float(r.variance_percent), "provider": r.provider_key},
            )
            alerts.append({
                "provider_key":     r.provider_key,
                "variance_percent": float(r.variance_percent),
                "severity":         r.severity,
                "estimate_id":      r.estimate_id,
                "created_at":       r.created_at.isoformat(),
            })

        db.commit()
        return alerts

    def get_alerts(self, workspace_id: str = None, is_resolved: bool = False,
                   db: Session = None) -> list[dict]:
        query = db.query(EconomicsAlert).filter(EconomicsAlert.is_resolved == is_resolved)
        if workspace_id:
            query = query.filter(EconomicsAlert.workspace_id == workspace_id)
        rows = query.order_by(EconomicsAlert.created_at.desc()).limit(50).all()
        return [
            {"id": str(r.id), "alert_type": r.alert_type, "severity": r.severity,
             "title": r.title, "description": r.description,
             "is_resolved": r.is_resolved, "created_at": r.created_at.isoformat()}
            for r in rows
        ]

    def _create_alert(self, db, alert_type, severity, workspace_id, title, desc, evidence):
        a = EconomicsAlert(
            alert_type=alert_type, severity=severity, workspace_id=workspace_id,
            title=title, description=desc, evidence=evidence,
        )
        db.add(a)
