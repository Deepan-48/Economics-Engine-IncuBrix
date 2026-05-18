"""
services/analytics_service.py

Tracks the four analytics events defined in PRD Section 20.
Events are stored in the analytics_events table.

ECO-FR-060 : economics_estimate_created
ECO-FR-061 : economics_budget_blocked
ECO-FR-062 : economics_async_savings_recommended
ECO-FR-063 : economics_override_submitted (actual_vs_estimate placeholder)
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from models.analytics_event import AnalyticsEvent


class AnalyticsService:

    def __init__(self, db: Session):
        self.db = db

    def track_estimate_created(
        self,
        request_id: str,
        use_case: str,
        provider: str,
        estimated_base_cost: float,
        budget_status: str,
    ):
        self._save("economics_estimate_created", request_id, {
            "use_case": use_case,
            "provider": provider,
            "estimated_base_cost": estimated_base_cost,
            "budget_status": budget_status,
        })

    def track_budget_blocked(
        self,
        request_id: str,
        provider: str,
        estimated_high_cost: float,
        cap: float,
    ):
        self._save("economics_budget_blocked", request_id, {
            "provider": provider,
            "estimated_high_cost": estimated_high_cost,
            "cap": cap,
        })

    def track_async_savings(
        self,
        request_id: str,
        provider: str,
        estimated_savings: float,
    ):
        self._save("economics_async_savings_recommended", request_id, {
            "provider": provider,
            "estimated_savings": estimated_savings,
        })

    def track_override(
        self,
        request_id: str,
        original_provider: str,
        override_provider: str,
    ):
        # ECO-FR-063 placeholder — actual vs estimate tracked here in future
        self._save("economics_override_submitted", request_id, {
            "original_provider": original_provider,
            "override_provider": override_provider,
            "actual_cost": None,  # placeholder for future use
        })

    def _save(self, event_type: str, request_id: str, properties: dict):
        event = AnalyticsEvent(
            event_type=event_type,
            request_id=request_id,
            properties=properties,
        )
        self.db.add(event)
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"[analytics] failed to save {event_type}: {e}")
