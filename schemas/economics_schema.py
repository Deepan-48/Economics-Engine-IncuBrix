"""
schemas/economics_schema.py

Pydantic v2 schemas for:
  - EconomicsRequestIn   — validated input payload (ECO-FR-001 to 005)
  - RouteEstimate        — single provider cost result
  - EconomicsResponseOut — full API response including recommendation + alternatives
  - OverrideRequestIn    — payload for manual override endpoint
  - SimulateRequestIn    — simulation mode wrapper (same fields as request)
"""

from __future__ import annotations
from pydantic import BaseModel, Field, model_validator, field_validator
from typing import Optional, List
from enum import Enum
import uuid


# ---------------------------------------------------------------------------
# Enums matching PRD Section 10.2
# ---------------------------------------------------------------------------

class UseCase(str, Enum):
    article_to_social       = "article_to_social"
    script_to_social        = "script_to_social_variants"
    brand_marketing         = "brand_marketing_post_to_promo"
    blog_to_explainer       = "blog_product_copy_to_explainer"
    campaign_variant        = "campaign_variant_generation"
    short_form_social       = "short_form_social_video"


class DurationClass(str, Enum):
    short  = "short"    # ~8 seconds
    medium = "medium"   # ~20 seconds
    long   = "long"     # ~45 seconds


class QualityBar(str, Enum):
    acceptable = "acceptable"
    high       = "high"
    premium    = "premium"


class LatencyMode(str, Enum):
    fastest   = "fastest"
    balanced  = "balanced"
    async_ok  = "async_ok"


class BudgetMode(str, Enum):
    cheapest  = "cheapest"
    balanced  = "balanced"
    premium   = "premium"


class MarkupMode(str, Enum):
    pass_through     = "pass_through"
    markup           = "markup"
    protected_margin = "protected_margin"


# ---------------------------------------------------------------------------
# Input schema — ECO-FR-001, 002, 003, 005
# ---------------------------------------------------------------------------

class EconomicsRequestIn(BaseModel):
    """
    Full input payload for a cost estimation request.
    All required fields must be present; validation rejects missing ones (ECO-FR-005).
    """

    request_id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Client-supplied or auto-generated request UUID",
    )

    # Required fields (ECO-FR-002)
    use_case: UseCase = Field(..., description="Core economics decision key")
    duration_class: DurationClass = Field(..., description="short | medium | long")
    quality_bar: QualityBar = Field(..., description="acceptable | high | premium")
    latency_mode: LatencyMode = Field(..., description="fastest | balanced | async_ok")
    batch_size: int = Field(..., ge=1, le=10000, description="Number of videos in this job")
    budget_mode: BudgetMode = Field(..., description="cheapest | balanced | premium")

    # Optional budget caps (ECO-FR-003)
    job_budget_cap: Optional[float] = Field(
        default=None, ge=0.0, description="Per-job ceiling in USD"
    )
    workspace_budget_cap: Optional[float] = Field(
        default=None, ge=0.0, description="Workspace-level policy ceiling in USD"
    )

    # Optional margin fields (ECO-FR-004 — Sprint 2, accepted but unused in S1)
    price_to_customer: Optional[float] = Field(
        default=None, ge=0.0, description="Customer-facing price for margin simulation"
    )
    target_margin_percent: Optional[float] = Field(
        default=None, ge=0.0, le=100.0, description="Target gross margin %"
    )
    markup_mode: Optional[MarkupMode] = Field(
        default=None, description="Markup policy mode"
    )

    # Simulation mode — always true for MVP (ECO-FR-001)
    simulation_mode: bool = Field(
        default=True, description="Always true for MVP; no live provider calls"
    )

    @field_validator("batch_size")
    @classmethod
    def batch_size_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("batch_size must be at least 1")
        return v

    @model_validator(mode="after")
    def validate_budget_logic(self) -> "EconomicsRequestIn":
        """
        If both job_budget_cap and workspace_budget_cap are provided,
        workspace cap must be >= job cap (it's the outer limit).
        """
        if (
            self.job_budget_cap is not None
            and self.workspace_budget_cap is not None
            and self.workspace_budget_cap < self.job_budget_cap
        ):
            raise ValueError(
                "workspace_budget_cap must be >= job_budget_cap "
                f"(got workspace={self.workspace_budget_cap}, job={self.job_budget_cap})"
            )
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "use_case": "script_to_social_variants",
                "duration_class": "short",
                "quality_bar": "high",
                "latency_mode": "async_ok",
                "batch_size": 10,
                "budget_mode": "balanced",
                "job_budget_cap": 25.00,
                "workspace_budget_cap": 500.00,
                "simulation_mode": True,
            }
        }
    }


# ---------------------------------------------------------------------------
# Output schemas
# ---------------------------------------------------------------------------

class RouteEstimate(BaseModel):
    """Cost estimate for a single provider route."""
    provider: str
    estimated_base_cost: float
    estimated_low_cost: float
    estimated_high_cost: float
    budget_status: str          # safe | warning | blocked
    cost_class: str             # low | medium | high
    confidence_class: str       # high | medium | low
    final_score: Optional[float] = None
    explanation: str
    is_async_batch: bool = False
    async_savings_percent: Optional[float] = None


class EconomicsResponseOut(BaseModel):
    """Full response returned by POST /estimate."""
    request_id: str
    recommended_route: Optional[RouteEstimate] = None
    alternatives: List[RouteEstimate] = []
    all_routes: List[RouteEstimate] = []
    request_status: str          # completed | blocked | failed
    blocked_reason: Optional[str] = None
    simulation_mode: bool = True


class OverrideRequestIn(BaseModel):
    """Payload for POST /estimate/{request_id}/override."""
    override_provider: str = Field(..., description="Provider key to use instead")
    override_reason: Optional[str] = Field(
        default=None, description="Why the user is overriding"
    )


class OverrideResponseOut(BaseModel):
    """Response after a manual override is stored."""
    request_id: str
    original_provider: str
    override_provider: str
    override_reason: Optional[str]
    stored: bool = True
