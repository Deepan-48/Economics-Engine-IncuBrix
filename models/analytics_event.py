"""
models/analytics_event.py

Stores analytics events for the four event types in PRD Section 20.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime

from db.database import Base
from models.economics_request import GUID, JSONType


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(128), nullable=False, index=True)
    request_id = Column(String(36), nullable=True, index=True)
    properties = Column(JSONType(), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<AnalyticsEvent {self.event_type} req={self.request_id}>"
