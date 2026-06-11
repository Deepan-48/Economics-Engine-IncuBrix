import uuid, json
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.types import TypeDecorator
from sqlalchemy.dialects.postgresql import UUID, JSONB
from db.database import Base

class GUID(TypeDecorator):
    impl = String; cache_ok = True
    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(UUID() if dialect.name == "postgresql" else String(36))
    def process_bind_param(self, value, dialect): return str(value) if value else None
    def process_result_value(self, value, dialect): return str(value) if value else None

class JSONType(TypeDecorator):
    impl = Text; cache_ok = True
    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(JSONB() if dialect.name == "postgresql" else Text())
    def process_bind_param(self, value, dialect):
        if value is None: return None
        return value if dialect.name == "postgresql" else json.dumps(value)
    def process_result_value(self, value, dialect):
        if value is None: return None
        return value if isinstance(value, (dict, list)) else json.loads(value)

class EconomicsRequest(Base):
    __tablename__ = "economics_requests"
    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_payload = Column(JSONType(), nullable=False)
    status = Column(String(32), nullable=False, default="completed")
    recommended_route = Column(String(128), nullable=True)
    simulation_mode = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
