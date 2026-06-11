from __future__ import annotations
from pydantic import BaseModel, Field, model_validator, field_validator
from typing import Optional, List
from enum import Enum
import uuid

class UseCase(str, Enum):
    article_to_social = "article_to_social"
    script_to_social  = "script_to_social_variants"
    brand_marketing   = "brand_marketing_post_to_promo"
    blog_to_explainer = "blog_product_copy_to_explainer"
    campaign_variant  = "campaign_variant_generation"
    short_form_social = "short_form_social_video"

class DurationClass(str, Enum):
    short = "short"; medium = "medium"; long = "long"

class QualityBar(str, Enum):
    acceptable = "acceptable"; high = "high"; premium = "premium"

class LatencyMode(str, Enum):
    fastest = "fastest"; balanced = "balanced"; async_ok = "async_ok"

class BudgetMode(str, Enum):
    cheapest = "cheapest"; balanced = "balanced"; premium = "premium"

class MarkupMode(str, Enum):
    pass_through = "pass_through"; markup = "markup"; protected_margin = "protected_margin"

class EconomicsRequestIn(BaseModel):
    request_id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    use_case: UseCase
    duration_class: DurationClass
    quality_bar: QualityBar
    latency_mode: LatencyMode
    batch_size: int = Field(..., ge=1, le=10000)
    budget_mode: BudgetMode
    job_budget_cap: Optional[float] = Field(default=None, ge=0.0)
    workspace_budget_cap: Optional[float] = Field(default=None, ge=0.0)
    price_to_customer: Optional[float] = Field(default=None, ge=0.0)
    target_margin_percent: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    markup_mode: Optional[MarkupMode] = None
    simulation_mode: bool = True
    @model_validator(mode="after")
    def validate_budget_logic(self):
        if self.job_budget_cap and self.workspace_budget_cap and self.workspace_budget_cap < self.job_budget_cap:
            raise ValueError("workspace_budget_cap must be >= job_budget_cap")
        return self

class RouteEstimate(BaseModel):
    provider: str
    estimated_base_cost: float
    estimated_low_cost: float
    estimated_high_cost: float
    budget_status: str
    cost_class: str
    confidence_class: str
    final_score: Optional[float] = None
    explanation: str
    is_async_batch: bool = False
    async_savings_percent: Optional[float] = None

class EconomicsResponseOut(BaseModel):
    request_id: str
    recommended_route: Optional[RouteEstimate] = None
    alternatives: List[RouteEstimate] = []
    all_routes: List[RouteEstimate] = []
    request_status: str
    blocked_reason: Optional[str] = None
    simulation_mode: bool = True

class OverrideRequestIn(BaseModel):
    override_provider: str
    override_reason: Optional[str] = None

class OverrideResponseOut(BaseModel):
    request_id: str
    original_provider: str
    override_provider: str
    override_reason: Optional[str]
    stored: bool = True
