"""
schemas_v2/economics_v2_schema.py
"""

from __future__ import annotations
from pydantic import BaseModel, Field, model_validator
from typing import Optional, List
from enum import Enum
import uuid


class ExecutionMode(str, Enum):
    sync        = "sync"
    batch       = "batch"
    async_queue = "async_queue"
    deferred    = "deferred"


class ResolutionClass(str, Enum):
    r_720p  = "720p"
    r_1080p = "1080p"
    r_4k    = "4k"


class BudgetStatus(str, Enum):
    safe               = "safe"
    warn_near_cap      = "warn_near_cap"
    blocked_hard_cap   = "blocked_hard_cap"
    blocked_margin     = "blocked_margin"
    review_required    = "review_required"
    approved_exception = "approved_exception"
    reserved           = "reserved"
    settled            = "settled"
    released           = "released"


class ApprovalStatus(str, Enum):
    draft       = "draft"
    staged      = "staged"
    approved    = "approved"
    active      = "active"
    inactive    = "inactive"
    rolled_back = "rolled_back"


class PricingSourceType(str, Enum):
    manual          = "manual"
    imported_csv    = "imported_csv"
    provider_api    = "provider_api"
    invoice_actual  = "invoice_actual"
    estimated_proxy = "estimated_proxy"


class BillingUnitType(str, Enum):
    per_second               = "per_second"
    per_frame                = "per_frame"
    per_output               = "per_output"
    per_minute               = "per_minute"
    per_token                = "per_token"
    per_api_call             = "per_api_call"
    per_runtime_second       = "per_runtime_second"
    gpu_time                 = "gpu_time"
    credits                  = "credits"
    storage                  = "storage"
    bandwidth                = "bandwidth"
    flat_fee                 = "flat_fee"
    subscription_entitlement = "subscription_entitlement"
    account_mode_multiplier  = "account_mode_multiplier"
    custom_formula           = "custom_formula"


class LedgerEntryType(str, Enum):
    estimated   = "estimated"
    reserved    = "reserved"
    committed   = "committed"
    actual      = "actual"
    adjusted    = "adjusted"
    released    = "released"
    refunded    = "refunded"
    written_off = "written_off"


class VarianceSeverity(str, Enum):
    low      = "low"
    medium   = "medium"
    high     = "high"
    critical = "critical"


# reuse from v1
from schemas.economics_schema import (
    UseCase, DurationClass, QualityBar,
    LatencyMode, BudgetMode, MarkupMode,
)


class CandidateRoute(BaseModel):
    provider_key:   str
    model_key:      str = "default"
    execution_mode: ExecutionMode = ExecutionMode.sync


class EstimateRequestV2(BaseModel):
    schema_version:  str = "economics.estimate.request.v2"
    request_id:      str = Field(default_factory=lambda: str(uuid.uuid4()))
    idempotency_key: Optional[str] = None
    correlation_id:  str = Field(default_factory=lambda: str(uuid.uuid4()))

    workspace_id: Optional[str] = None
    project_id:   Optional[str] = None
    campaign_id:  Optional[str] = None
    actor_id:     Optional[str] = None

    use_case:       UseCase
    duration_class: DurationClass
    quality_bar:    QualityBar
    latency_mode:   LatencyMode
    batch_size:     int = Field(..., ge=1)
    variant_count:  int = Field(default=1, ge=1)
    budget_mode:    BudgetMode

    expected_duration_seconds: Optional[int] = None
    resolution_class:          Optional[ResolutionClass] = None
    output_type:               Optional[str] = None
    target_platform:           Optional[str] = None

    candidate_routes: List[CandidateRoute] = []

    job_budget_cap:        Optional[float] = None
    workspace_budget_cap:  Optional[float] = None
    campaign_budget_cap:   Optional[float] = None
    currency:              str = "USD"
    price_to_customer:     Optional[float] = None
    target_margin_percent: Optional[float] = None
    markup_mode:           Optional[MarkupMode] = None

    simulation_mode:     bool = True
    require_reservation: bool = False

    @model_validator(mode="after")
    def check_caps(self):
        if (
            self.job_budget_cap is not None
            and self.workspace_budget_cap is not None
            and self.workspace_budget_cap < self.job_budget_cap
        ):
            raise ValueError("workspace_budget_cap must be >= job_budget_cap")
        return self


class RateCard(BaseModel):
    model_key:     str = "default"
    unit_type:     BillingUnitType
    unit_rate:     float
    quality_class: Optional[str] = None
    currency:      str = "USD"


class PricingModifier(BaseModel):
    modifier_type: str
    value_type:    str
    value:         float
    condition:     Optional[str] = None


class CostComponent(BaseModel):
    unit_type:            str
    unit_quantity:        float
    unit_rate:            float
    currency:             str = "USD"
    modifier_applied:     Optional[str] = None
    low_cost:             float
    base_cost:            float
    high_cost:            float
    formula_version:      str = "v2.0"
    contribution_percent: Optional[float] = None


class EstimateResultV2(BaseModel):
    schema_version:           str = "economics.estimate.result.v2"
    estimate_id:              str = Field(default_factory=lambda: str(uuid.uuid4()))
    request_id:               str
    job_fingerprint:          Optional[str] = None
    pricing_profile_versions: List[str] = []
    policy_version:           str = "v2.0"
    formula_version:          str = "v2.0"

    provider_key:          str
    model_key:             str = "default"
    execution_mode:        str = "sync"
    estimated_low_cost:    float
    estimated_base_cost:   float
    estimated_high_cost:   float
    currency:              str = "USD"
    confidence_class:      str
    cost_class:            str
    budget_status:         str
    margin_status:         str = "safe"
    final_score:           Optional[float] = None
    explanation:           str
    cost_components:       List[CostComponent] = []
    cost_drivers:          List[dict] = []
    is_async_batch:        bool = False
    async_savings_percent: Optional[float] = None
    retry_exposure:        Optional[float] = None
    per_output_cost:       Optional[float] = None


class FullEstimateResponse(BaseModel):
    request_id:            str
    correlation_id:        str
    recommended_route:     Optional[EstimateResultV2] = None
    alternatives:          List[EstimateResultV2] = []
    blocked_routes:        List[EstimateResultV2] = []
    all_routes:            List[EstimateResultV2] = []
    request_status:        str
    blocked_reason:        Optional[str] = None
    savings_delta_vs_next: Optional[float] = None
    fallback_exposure:     Optional[dict] = None
    margin_simulation:     Optional[dict] = None
    batch_recommendation:  Optional[dict] = None
    simulation_mode:       bool = True
    reservation_id:        Optional[str] = None
    job_fingerprint:       Optional[str] = None


class BudgetReservationIn(BaseModel):
    estimate_id:    str
    workspace_id:   Optional[str] = None
    campaign_id:    Optional[str] = None
    scope_type:     str = "job"
    scope_id:       Optional[str] = None
    reserved_amount: float
    currency:       str = "USD"
    expires_minutes: int = 60


class BudgetSettleIn(BaseModel):
    actual_amount: float
    notes:         Optional[str] = None


class BudgetReleaseIn(BaseModel):
    reason: Optional[str] = None


class ScenarioRunIn(BaseModel):
    scenario_name:         str
    use_case:              UseCase
    duration_class:        DurationClass
    quality_bar:           QualityBar
    latency_mode:          LatencyMode
    batch_size:            int = Field(..., ge=1)
    variant_count:         int = 1
    budget_mode:           BudgetMode
    price_to_customer:     Optional[float] = None
    target_margin_percent: Optional[float] = None
    markup_mode:           Optional[MarkupMode] = None
    job_budget_cap:        Optional[float] = None
    compare_pricing_version: Optional[int] = None


class LedgerEntryIn(BaseModel):
    workspace_id: Optional[str] = None
    project_id:   Optional[str] = None
    campaign_id:  Optional[str] = None
    job_id:       Optional[str] = None
    provider_key: Optional[str] = None
    use_case:     Optional[str] = None
    entry_type:   LedgerEntryType
    amount:       float
    currency:     str = "USD"
    source_ref:   Optional[str] = None
    notes:        Optional[str] = None


class ActualCostImportIn(BaseModel):
    provider_key:       str
    provider_job_id:    Optional[str] = None
    provider_request_id: Optional[str] = None
    estimate_id:        Optional[str] = None
    job_id:             Optional[str] = None
    workspace_id:       Optional[str] = None
    actual_amount:      float
    currency:           str = "USD"
    billing_unit:       Optional[str] = None
    unit_quantity:      Optional[float] = None
    import_source:      str = "manual"
    notes:              Optional[str] = None


class ConfigValidateIn(BaseModel):
    provider_key:     str
    draft_profile:    dict
    run_golden_tests: bool = True


class StageProfileIn(BaseModel):
    profile_data: dict
    created_by:   str = "admin"


class OverrideV2In(BaseModel):
    override_provider: str
    override_reason:   str
    scope:             str = "single_job"
    authorized_by:     Optional[str] = None
