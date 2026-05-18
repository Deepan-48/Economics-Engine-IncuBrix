"""
models/economics_decision.py

ORM models for:
  - economics_decisions   (one per provider evaluated per request)
  - economics_overrides   (when user overrides the engine recommendation)
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Numeric
from sqlalchemy.orm import relationship

from db.database import Base
from models.economics_request import GUID


class EconomicsDecision(Base):
    __tablename__ = "economics_decisions"

    id = Column(
        GUID(),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    economics_request_id = Column(
        GUID(),
        ForeignKey("economics_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    provider_key = Column(String(64), nullable=False, index=True)

    # Cost estimates (in USD)
    estimated_low_cost = Column(Numeric(10, 4), nullable=False)
    estimated_high_cost = Column(Numeric(10, 4), nullable=False)
    estimated_base_cost = Column(Numeric(10, 4), nullable=False)

    # Policy & scoring
    budget_status = Column(String(32), nullable=False, default="safe")
    # safe | warning | blocked

    cost_class = Column(String(16), nullable=False, default="medium")
    # low | medium | high

    confidence_class = Column(String(16), nullable=False, default="medium")
    # high | medium | low

    final_score = Column(Numeric(6, 4), nullable=True)
    is_recommended = Column(Boolean, nullable=False, default=False)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return (
            f"<EconomicsDecision provider={self.provider_key} "
            f"base=${self.estimated_base_cost} status={self.budget_status}>"
        )

    def to_dict(self) -> dict:
        return {
            "provider": self.provider_key,
            "estimated_base_cost": float(self.estimated_base_cost),
            "estimated_low_cost": float(self.estimated_low_cost),
            "estimated_high_cost": float(self.estimated_high_cost),
            "budget_status": self.budget_status,
            "cost_class": self.cost_class,
            "confidence_class": self.confidence_class,
            "final_score": float(self.final_score) if self.final_score else None,
            "is_recommended": self.is_recommended,
            "explanation": self.explanation,
        }


class EconomicsOverride(Base):
    __tablename__ = "economics_overrides"

    id = Column(
        GUID(),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    economics_request_id = Column(
        GUID(),
        ForeignKey("economics_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_provider = Column(String(64), nullable=False)
    override_provider = Column(String(64), nullable=False)
    override_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return (
            f"<EconomicsOverride {self.original_provider} → {self.override_provider}>"
        )
