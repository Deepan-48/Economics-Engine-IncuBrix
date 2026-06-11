import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Numeric
from db.database import Base
from models.economics_request import GUID

class EconomicsDecision(Base):
    __tablename__ = "economics_decisions"
    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    economics_request_id = Column(GUID(), ForeignKey("economics_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_key = Column(String(64), nullable=False)
    estimated_low_cost = Column(Numeric(10, 4), nullable=False)
    estimated_high_cost = Column(Numeric(10, 4), nullable=False)
    estimated_base_cost = Column(Numeric(10, 4), nullable=False)
    budget_status = Column(String(32), nullable=False, default="safe")
    cost_class = Column(String(16), nullable=False, default="medium")
    confidence_class = Column(String(16), nullable=False, default="medium")
    final_score = Column(Numeric(6, 4), nullable=True)
    is_recommended = Column(Boolean, nullable=False, default=False)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    def to_dict(self):
        return {"provider": self.provider_key, "estimated_base_cost": float(self.estimated_base_cost), "estimated_low_cost": float(self.estimated_low_cost), "estimated_high_cost": float(self.estimated_high_cost), "budget_status": self.budget_status, "cost_class": self.cost_class, "confidence_class": self.confidence_class, "final_score": float(self.final_score) if self.final_score else None, "is_recommended": self.is_recommended, "explanation": self.explanation}

class EconomicsOverride(Base):
    __tablename__ = "economics_overrides"
    id = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    economics_request_id = Column(GUID(), ForeignKey("economics_requests.id", ondelete="CASCADE"), nullable=False)
    original_provider = Column(String(64), nullable=False)
    override_provider = Column(String(64), nullable=False)
    override_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
