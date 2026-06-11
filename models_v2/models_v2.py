"""
models_v2/models_v2.py
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Numeric, Text, ForeignKey
from db.database import Base
from models.economics_request import GUID, JSONType


class PricingProfileV2(Base):
    __tablename__ = "v2_pricing_profiles"

    id              = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_key    = Column(String(64), nullable=False, index=True)
    model_key       = Column(String(128), nullable=False, default="default")
    profile_version = Column(Integer, nullable=False, default=1)
    environment     = Column(String(32), nullable=False, default="production")
    source_type     = Column(String(32), nullable=False, default="manual")
    approval_status = Column(String(32), nullable=False, default="active")
    effective_from  = Column(DateTime, nullable=True)
    effective_to    = Column(DateTime, nullable=True)
    currency        = Column(String(8), nullable=False, default="USD")
    profile_data    = Column(JSONType(), nullable=False)
    rate_cards      = Column(JSONType(), nullable=True)
    modifiers       = Column(JSONType(), nullable=True)
    is_active       = Column(Boolean, nullable=False, default=True)
    created_at      = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at      = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        d = {
            "id":              str(self.id),
            "provider_key":    self.provider_key,
            "model_key":       self.model_key,
            "profile_version": self.profile_version,
            "environment":     self.environment,
            "source_type":     self.source_type,
            "approval_status": self.approval_status,
            "currency":        self.currency,
            "is_active":       self.is_active,
            "rate_cards":      self.rate_cards or [],
            "modifiers":       self.modifiers or [],
        }
        d.update(self.profile_data or {})
        return d


class EconomicsEstimateV2(Base):
    __tablename__ = "v2_estimates"

    id                      = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    request_id              = Column(String(36), nullable=False, index=True)
    correlation_id          = Column(String(36), nullable=True)
    idempotency_key         = Column(String(256), nullable=True, unique=True)
    job_fingerprint         = Column(String(64), nullable=True)
    workspace_id            = Column(String(36), nullable=True, index=True)
    project_id              = Column(String(36), nullable=True)
    campaign_id             = Column(String(36), nullable=True)
    provider_key            = Column(String(64), nullable=False)
    model_key               = Column(String(128), nullable=False, default="default")
    execution_mode          = Column(String(32), nullable=False, default="sync")
    estimated_low_cost      = Column(Numeric(12, 4), nullable=False)
    estimated_base_cost     = Column(Numeric(12, 4), nullable=False)
    estimated_high_cost     = Column(Numeric(12, 4), nullable=False)
    currency                = Column(String(8), nullable=False, default="USD")
    confidence_class        = Column(String(16), nullable=False)
    cost_class              = Column(String(16), nullable=False)
    budget_status           = Column(String(32), nullable=False, default="safe")
    margin_status           = Column(String(32), nullable=False, default="safe")
    final_score             = Column(Numeric(8, 4), nullable=True)
    is_recommended          = Column(Boolean, nullable=False, default=False)
    explanation             = Column(Text, nullable=True)
    cost_components         = Column(JSONType(), nullable=True)
    cost_drivers            = Column(JSONType(), nullable=True)
    pricing_profile_version = Column(String(64), nullable=True)
    policy_version          = Column(String(16), nullable=False, default="v2.0")
    formula_version         = Column(String(16), nullable=False, default="v2.0")
    is_async_batch          = Column(Boolean, nullable=False, default=False)
    async_savings_percent   = Column(Numeric(6, 2), nullable=True)
    retry_exposure          = Column(Numeric(12, 4), nullable=True)
    per_output_cost         = Column(Numeric(12, 4), nullable=True)
    simulation_mode         = Column(Boolean, nullable=False, default=True)
    created_at              = Column(DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "estimate_id":             str(self.id),
            "provider":                self.provider_key,
            "model_key":               self.model_key,
            "execution_mode":          self.execution_mode,
            "estimated_base_cost":     float(self.estimated_base_cost),
            "estimated_low_cost":      float(self.estimated_low_cost),
            "estimated_high_cost":     float(self.estimated_high_cost),
            "currency":                self.currency,
            "confidence_class":        self.confidence_class,
            "cost_class":              self.cost_class,
            "budget_status":           self.budget_status,
            "margin_status":           self.margin_status,
            "final_score":             float(self.final_score) if self.final_score else None,
            "is_recommended":          self.is_recommended,
            "explanation":             self.explanation,
            "cost_components":         self.cost_components or [],
            "cost_drivers":            self.cost_drivers or [],
            "pricing_profile_version": self.pricing_profile_version,
            "policy_version":          self.policy_version,
            "formula_version":         self.formula_version,
            "is_async_batch":          self.is_async_batch,
            "async_savings_percent":   float(self.async_savings_percent) if self.async_savings_percent else None,
            "retry_exposure":          float(self.retry_exposure) if self.retry_exposure else None,
            "per_output_cost":         float(self.per_output_cost) if self.per_output_cost else None,
        }


class BudgetReservation(Base):
    __tablename__ = "v2_budget_reservations"

    id              = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    estimate_id     = Column(String(36), nullable=False, index=True)
    workspace_id    = Column(String(36), nullable=True, index=True)
    campaign_id     = Column(String(36), nullable=True)
    scope_type      = Column(String(32), nullable=False, default="job")
    scope_id        = Column(String(36), nullable=True)
    reserved_amount = Column(Numeric(12, 4), nullable=False)
    currency        = Column(String(8), nullable=False, default="USD")
    status          = Column(String(32), nullable=False, default="reserved")
    expires_at      = Column(DateTime, nullable=True)
    settled_amount  = Column(Numeric(12, 4), nullable=True)
    released_amount = Column(Numeric(12, 4), nullable=True)
    created_at      = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at      = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class LedgerEntry(Base):
    __tablename__ = "v2_ledger_entries"

    id           = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), nullable=True, index=True)
    project_id   = Column(String(36), nullable=True)
    campaign_id  = Column(String(36), nullable=True, index=True)
    job_id       = Column(String(36), nullable=True, index=True)
    provider_key = Column(String(64), nullable=True)
    use_case     = Column(String(128), nullable=True)
    entry_type   = Column(String(32), nullable=False, index=True)
    amount       = Column(Numeric(12, 4), nullable=False)
    currency     = Column(String(8), nullable=False, default="USD")
    source_ref   = Column(String(128), nullable=True)
    notes        = Column(Text, nullable=True)
    created_at   = Column(DateTime, nullable=False, default=datetime.utcnow)


class EconomicsScenario(Base):
    __tablename__ = "v2_scenarios"

    id             = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    scenario_name  = Column(String(256), nullable=False)
    input_config   = Column(JSONType(), nullable=False)
    result_summary = Column(JSONType(), nullable=True)
    status         = Column(String(32), nullable=False, default="completed")
    created_at     = Column(DateTime, nullable=False, default=datetime.utcnow)


class ConfigVersion(Base):
    __tablename__ = "v2_config_versions"

    id                = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_key      = Column(String(64), nullable=False, index=True)
    version_number    = Column(Integer, nullable=False)
    approval_status   = Column(String(32), nullable=False, default="staged")
    draft_profile     = Column(JSONType(), nullable=False)
    validation_result = Column(JSONType(), nullable=True)
    impact_preview    = Column(JSONType(), nullable=True)
    approved_by       = Column(String(128), nullable=True)
    created_by        = Column(String(128), nullable=True)
    activated_at      = Column(DateTime, nullable=True)
    created_at        = Column(DateTime, nullable=False, default=datetime.utcnow)


class ActualCostRecord(Base):
    __tablename__ = "v2_actual_costs"

    id                  = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    provider_key        = Column(String(64), nullable=False, index=True)
    provider_job_id     = Column(String(256), nullable=True)
    provider_request_id = Column(String(256), nullable=True)
    estimate_id         = Column(String(36), nullable=True, index=True)
    job_id              = Column(String(36), nullable=True, index=True)
    workspace_id        = Column(String(36), nullable=True, index=True)
    actual_amount       = Column(Numeric(12, 4), nullable=False)
    currency            = Column(String(8), nullable=False, default="USD")
    billing_unit        = Column(String(64), nullable=True)
    unit_quantity       = Column(Numeric(12, 4), nullable=True)
    import_source       = Column(String(32), nullable=False, default="manual")
    map_status          = Column(String(32), nullable=False, default="unmapped")
    notes               = Column(Text, nullable=True)
    created_at          = Column(DateTime, nullable=False, default=datetime.utcnow)


class CostVarianceRecord(Base):
    __tablename__ = "v2_cost_variances"

    id               = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    estimate_id      = Column(String(36), nullable=False, index=True)
    actual_cost_id   = Column(String(36), nullable=False)
    provider_key     = Column(String(64), nullable=False)
    workspace_id     = Column(String(36), nullable=True)
    estimated_amount = Column(Numeric(12, 4), nullable=False)
    actual_amount    = Column(Numeric(12, 4), nullable=False)
    variance_amount  = Column(Numeric(12, 4), nullable=False)
    variance_percent = Column(Numeric(8, 2), nullable=False)
    variance_reason  = Column(String(256), nullable=True)
    severity         = Column(String(16), nullable=False, default="low")
    created_at       = Column(DateTime, nullable=False, default=datetime.utcnow)


class EconomicsAlert(Base):
    __tablename__ = "v2_economics_alerts"

    id             = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_type     = Column(String(64), nullable=False, index=True)
    severity       = Column(String(16), nullable=False, default="medium")
    workspace_id   = Column(String(36), nullable=True, index=True)
    provider_key   = Column(String(64), nullable=True)
    title          = Column(String(256), nullable=False)
    description    = Column(Text, nullable=True)
    evidence       = Column(JSONType(), nullable=True)
    is_resolved    = Column(Boolean, nullable=False, default=False)
    created_at     = Column(DateTime, nullable=False, default=datetime.utcnow)


class EconomicsEventV2(Base):
    __tablename__ = "v2_events"

    id             = Column(GUID(), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type     = Column(String(128), nullable=False, index=True)
    schema_version = Column(String(16), nullable=False, default="v2.0")
    correlation_id = Column(String(36), nullable=True, index=True)
    request_id     = Column(String(36), nullable=True, index=True)
    workspace_id   = Column(String(36), nullable=True, index=True)
    properties     = Column(JSONType(), nullable=True)
    created_at     = Column(DateTime, nullable=False, default=datetime.utcnow)
