from datetime import datetime
from sqlalchemy.orm import Session
from models.analytics_event import AnalyticsEvent

class AnalyticsService:
    def __init__(self, db):
        self.db = db
    def track_estimate_created(self, request_id, use_case, provider, estimated_base_cost, budget_status):
        self._save("economics_estimate_created", request_id, {"use_case": use_case, "provider": provider, "estimated_base_cost": estimated_base_cost, "budget_status": budget_status})
    def track_budget_blocked(self, request_id, provider, estimated_high_cost, cap):
        self._save("economics_budget_blocked", request_id, {"provider": provider, "estimated_high_cost": estimated_high_cost, "cap": cap})
    def track_async_savings(self, request_id, provider, estimated_savings):
        self._save("economics_async_savings_recommended", request_id, {"provider": provider, "estimated_savings": estimated_savings})
    def track_override(self, request_id, original_provider, override_provider):
        self._save("economics_override_submitted", request_id, {"original_provider": original_provider, "override_provider": override_provider, "actual_cost": None})
    def _save(self, event_type, request_id, properties):
        e = AnalyticsEvent(event_type=event_type, request_id=request_id, properties=properties)
        self.db.add(e)
        try: self.db.commit()
        except Exception as ex: self.db.rollback(); print(f"[analytics] failed {event_type}: {ex}")
