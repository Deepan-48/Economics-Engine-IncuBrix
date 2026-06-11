import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, DateTime
from db.database import Base
from models.economics_request import GUID, JSONType

class PricingProfile(Base):
    __tablename__ = "pricing_profiles"
    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_key = Column(String(64), nullable=False, index=True)
    pricing_profile_json = Column(JSONType(), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    def to_dict(self):
        return {"id": str(self.id), "provider_key": self.provider_key, "version": self.version, "is_active": self.is_active, **self.pricing_profile_json}
