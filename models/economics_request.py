"""
models/economics_request.py

ORM model for the economics_requests table.
One row = one call to POST /api/video-economics/estimate
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.types import TypeDecorator, String as SAString
import json

from db.database import Base


# ---------------------------------------------------------------------------
# Cross-DB helpers: UUID and JSON work on both SQLite and PostgreSQL
# ---------------------------------------------------------------------------

class GUID(TypeDecorator):
    """Platform-independent UUID type.
    Uses PostgreSQL's UUID type, otherwise uses String(36)."""
    impl = SAString
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(UUID())
        return dialect.type_descriptor(SAString(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return str(value)


class JSONType(TypeDecorator):
    """Platform-independent JSON type."""
    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value
        return json.loads(value)


class EconomicsRequest(Base):
    __tablename__ = "economics_requests"

    id = Column(
        GUID(),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    request_payload = Column(JSONType(), nullable=False)
    status = Column(
        String(32),
        nullable=False,
        default="completed",
        # Values: completed | blocked | failed
    )
    recommended_route = Column(String(128), nullable=True)
    simulation_mode = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return (
            f"<EconomicsRequest id={self.id} "
            f"status={self.status} route={self.recommended_route}>"
        )
