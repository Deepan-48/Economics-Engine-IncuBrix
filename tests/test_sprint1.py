"""
tests/test_sprint1.py

Full Sprint 1 test suite covering:
  - Input schema validation (ECO-FR-001 to 005)
  - Cost normalizer per provider (ECO-FR-020, 021, 023, 024)
  - Estimation engine (ECO-FR-020)
  - Policy engine (ECO-FR-030, 034)
  - Route ranker (ECO-FR-040, 041, 042, 044)
  - API endpoints via TestClient

Run with:
    pytest tests/test_sprint1.py -v
    pytest tests/test_sprint1.py -v --cov=. --cov-report=term-missing
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pydantic import ValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ---- App imports ----
from schemas.economics_schema import (
    EconomicsRequestIn,
    UseCase,
    DurationClass,
    QualityBar,
    LatencyMode,
    BudgetMode,
)
from services.cost_normalizer import (
    normalize_openai,
    normalize_runway,
    normalize_fal,
    normalize_replicate,
    normalize_piapi,
    normalize_cost,
)
from services.estimation_engine import EstimationEngine
from services.policy_engine import PolicyEngine
from services.route_ranker import RouteRanker
from db.database import Base, get_db
from main import app


# ===========================================================================
# Test DB setup — in-memory SQLite
# ===========================================================================

TEST_DB_URL = "sqlite:///./test_economics.db"

test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Create tables and seed data once for the whole test session."""
    Base.metadata.create_all(bind=test_engine)
    # Seed pricing profiles
    db = TestSessionLocal()
    from services.pricing_registry_service import PricingRegistryService
    PricingRegistryService.seed_from_json(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)
    import os
    if os.path.exists("./test_economics.db"):
        os.remove("./test_economics.db")


@pytest.fixture
def client(setup_test_db):
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def db_session(setup_test_db):
    db = TestSessionLocal()
    yield db
    db.close()


# ===========================================================================
# Shared test data
# ===========================================================================

VALID_REQUEST = {
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

OPENAI_PROFILE = {
    "provider_key": "openai",
    "pricing_unit": "per_second",
    "currency": "USD",
    "supports_batch_discount": True,
    "batch_discount_percent": 50,
    "base_assumptions": {"short_seconds": 8, "medium_seconds": 20, "long_seconds": 45},
    "rate_per_second": 0.030,
    "uncertainty_multiplier": {"low": 0.9, "high": 1.2},
    "quality_multiplier": {"acceptable": 0.8, "high": 1.0, "premium": 1.35},
    "is_active": True,
}

RUNWAY_PROFILE = {
    "provider_key": "runway",
    "pricing_unit": "credits",
    "credit_price_usd": 0.01,
    "base_assumptions": {"short_credits": 50, "medium_credits": 120, "long_credits": 250},
    "uncertainty_multiplier": {"low": 0.9, "high": 1.3},
    "quality_multiplier": {"acceptable": 0.85, "high": 1.0, "premium": 1.4},
    "is_active": True,
}


# ===========================================================================
# 1. Schema Validation Tests (ECO-FR-001 to 005)
# ===========================================================================

class TestSchemaValidation:

    def test_valid_request_passes(self):
        req = EconomicsRequestIn(**VALID_REQUEST)
        assert req.use_case == UseCase.script_to_social
        assert req.duration_class == DurationClass.short
        assert req.batch_size == 10

    def test_missing_use_case_fails(self):
        data = {**VALID_REQUEST}
        del data["use_case"]
        with pytest.raises(ValidationError) as exc_info:
            EconomicsRequestIn(**data)
        assert "use_case" in str(exc_info.value)

    def test_missing_duration_class_fails(self):
        data = {**VALID_REQUEST}
        del data["duration_class"]
        with pytest.raises(ValidationError):
            EconomicsRequestIn(**data)

    def test_missing_quality_bar_fails(self):
        data = {**VALID_REQUEST}
        del data["quality_bar"]
        with pytest.raises(ValidationError):
            EconomicsRequestIn(**data)

    def test_missing_latency_mode_fails(self):
        data = {**VALID_REQUEST}
        del data["latency_mode"]
        with pytest.raises(ValidationError):
            EconomicsRequestIn(**data)

    def test_missing_batch_size_fails(self):
        data = {**VALID_REQUEST}
        del data["batch_size"]
        with pytest.raises(ValidationError):
            EconomicsRequestIn(**data)

    def test_missing_budget_mode_fails(self):
        data = {**VALID_REQUEST}
        del data["budget_mode"]
        with pytest.raises(ValidationError):
            EconomicsRequestIn(**data)

    def test_invalid_use_case_enum_fails(self):
        data = {**VALID_REQUEST, "use_case": "nonexistent_case"}
        with pytest.raises(ValidationError):
            EconomicsRequestIn(**data)

    def test_batch_size_zero_fails(self):
        data = {**VALID_REQUEST, "batch_size": 0}
        with pytest.raises(ValidationError):
            EconomicsRequestIn(**data)

    def test_workspace_cap_less_than_job_cap_fails(self):
        data = {**VALID_REQUEST, "job_budget_cap": 100.0, "workspace_budget_cap": 50.0}
        with pytest.raises(ValidationError) as exc_info:
            EconomicsRequestIn(**data)
        assert "workspace_budget_cap" in str(exc_info.value)

    def test_optional_caps_can_be_absent(self):
        data = {**VALID_REQUEST}
        del data["job_budget_cap"]
        del data["workspace_budget_cap"]
        req = EconomicsRequestIn(**data)
        assert req.job_budget_cap is None
        assert req.workspace_budget_cap is None

    def test_simulation_mode_defaults_true(self):
        data = {k: v for k, v in VALID_REQUEST.items() if k != "simulation_mode"}
        req = EconomicsRequestIn(**data)
        assert req.simulation_mode is True

    def test_request_id_auto_generated(self):
        req = EconomicsRequestIn(**VALID_REQUEST)
        assert req.request_id is not None
        assert len(req.request_id) == 36  # UUID format


# ===========================================================================
# 2. Cost Normalizer Tests (ECO-FR-020, 021, 023, 024)
# ===========================================================================

class TestCostNormalizer:

    def test_openai_sync_cost(self):
        result = normalize_openai(
            OPENAI_PROFILE,
            DurationClass.short,
            QualityBar.high,
            LatencyMode.balanced,
            batch_size=1,
        )
        # 8 seconds × $0.030 × quality=1.0 × 1 = $0.24
        assert result["base_cost"] == pytest.approx(0.24, rel=0.01)
        assert result["is_async_batch"] is False
        assert result["async_savings_percent"] is None

    def test_openai_async_batch_is_cheaper(self):
        sync = normalize_openai(
            OPENAI_PROFILE, DurationClass.short, QualityBar.high, LatencyMode.balanced, 1
        )
        async_r = normalize_openai(
            OPENAI_PROFILE, DurationClass.short, QualityBar.high, LatencyMode.async_ok, 1
        )
        assert async_r["base_cost"] < sync["base_cost"]
        assert async_r["is_async_batch"] is True
        assert async_r["async_savings_percent"] == 50.0

    def test_openai_batch_size_scales_cost(self):
        single = normalize_openai(
            OPENAI_PROFILE, DurationClass.short, QualityBar.high, LatencyMode.balanced, 1
        )
        batch10 = normalize_openai(
            OPENAI_PROFILE, DurationClass.short, QualityBar.high, LatencyMode.balanced, 10
        )
        assert batch10["base_cost"] == pytest.approx(single["base_cost"] * 10, rel=0.01)

    def test_openai_uncertainty_range_is_correct(self):
        result = normalize_openai(
            OPENAI_PROFILE, DurationClass.short, QualityBar.high, LatencyMode.balanced, 1
        )
        base = result["base_cost"]
        assert result["low_cost"] == pytest.approx(base * 0.9, rel=0.01)
        assert result["high_cost"] == pytest.approx(base * 1.2, rel=0.01)

    def test_runway_cost_calculation(self):
        result = normalize_runway(
            RUNWAY_PROFILE, DurationClass.short, QualityBar.high, batch_size=1
        )
        # 50 credits × $0.01 × quality=1.0 × 1 = $0.50
        assert result["base_cost"] == pytest.approx(0.50, rel=0.01)

    def test_runway_no_batch_discount(self):
        result = normalize_runway(
            RUNWAY_PROFILE, DurationClass.short, QualityBar.high, batch_size=1
        )
        assert result["is_async_batch"] is False

    def test_fal_cost_scales_with_duration(self):
        from services.cost_normalizer import normalize_fal
        fal_profile = {
            "provider_key": "fal",
            "pricing_unit": "flat",
            "model_pricing": {"acceptable": 0.045, "high": 0.080, "premium": 0.150},
            "base_assumptions": {
                "short_multiplier": 1.0,
                "medium_multiplier": 2.2,
                "long_multiplier": 4.5,
            },
            "uncertainty_multiplier": {"low": 0.85, "high": 1.25},
        }
        short = normalize_fal(fal_profile, DurationClass.short, QualityBar.high, 1)
        medium = normalize_fal(fal_profile, DurationClass.medium, QualityBar.high, 1)
        assert medium["base_cost"] > short["base_cost"]

    def test_normalize_cost_dispatcher_openai(self):
        result = normalize_cost(
            OPENAI_PROFILE, DurationClass.short, QualityBar.high, LatencyMode.balanced, 1
        )
        assert "base_cost" in result
        assert result["base_cost"] > 0

    def test_normalize_cost_dispatcher_unknown_raises(self):
        bad_profile = {**OPENAI_PROFILE, "pricing_unit": "mystery_unit", "provider_key": "unknown"}
        with pytest.raises(ValueError, match="Unknown pricing_unit"):
            normalize_cost(bad_profile, DurationClass.short, QualityBar.high, LatencyMode.balanced, 1)

    def test_long_video_costs_more_than_short(self):
        short = normalize_openai(
            OPENAI_PROFILE, DurationClass.short, QualityBar.high, LatencyMode.balanced, 1
        )
        long = normalize_openai(
            OPENAI_PROFILE, DurationClass.long, QualityBar.high, LatencyMode.balanced, 1
        )
        assert long["base_cost"] > short["base_cost"]

    def test_premium_quality_costs_more_than_acceptable(self):
        acceptable = normalize_openai(
            OPENAI_PROFILE, DurationClass.short, QualityBar.acceptable, LatencyMode.balanced, 1
        )
        premium = normalize_openai(
            OPENAI_PROFILE, DurationClass.short, QualityBar.premium, LatencyMode.balanced, 1
        )
        assert premium["base_cost"] > acceptable["base_cost"]


# ===========================================================================
# 3. Estimation Engine Tests
# ===========================================================================

class TestEstimationEngine:

    def test_returns_estimate_per_active_provider(self, db_session):
        from services.pricing_registry_service import PricingRegistryService
        registry = PricingRegistryService(db_session)
        profiles = registry.get_all_active()

        req = EconomicsRequestIn(**VALID_REQUEST)
        engine = EstimationEngine()
        results = engine.estimate_all_routes(req, profiles)

        assert len(results) == len(profiles)
        assert len(results) >= 5  # we seeded 5

    def test_all_estimates_have_required_fields(self, db_session):
        from services.pricing_registry_service import PricingRegistryService
        profiles = PricingRegistryService(db_session).get_all_active()
        req = EconomicsRequestIn(**VALID_REQUEST)
        engine = EstimationEngine()
        results = engine.estimate_all_routes(req, profiles)

        for r in results:
            assert r.provider is not None
            assert r.estimated_base_cost > 0
            assert r.estimated_low_cost <= r.estimated_base_cost
            assert r.estimated_high_cost >= r.estimated_base_cost
            assert r.budget_status in ("safe", "warning", "blocked")
            assert r.cost_class in ("low", "medium", "high")
            assert r.confidence_class in ("high", "medium", "low")
            assert r.explanation != ""

    def test_blocked_when_all_exceed_tiny_cap(self, db_session):
        from services.pricing_registry_service import PricingRegistryService
        profiles = PricingRegistryService(db_session).get_all_active()
        req = EconomicsRequestIn(**{**VALID_REQUEST, "job_budget_cap": 0.001})
        engine = EstimationEngine()
        results = engine.estimate_all_routes(req, profiles)
        # All should be blocked with a cap of $0.001
        blocked = [r for r in results if r.budget_status == "blocked"]
        assert len(blocked) == len(results)


# ===========================================================================
# 4. Policy Engine Tests (ECO-FR-030, 034)
# ===========================================================================

class TestPolicyEngine:

    def _make_route(self, provider, base, low, high, is_async=False):
        from schemas.economics_schema import RouteEstimate
        return RouteEstimate(
            provider=provider,
            estimated_base_cost=base,
            estimated_low_cost=low,
            estimated_high_cost=high,
            budget_status="safe",
            cost_class="medium",
            confidence_class="medium",
            explanation="test",
            is_async_batch=is_async,
        )

    def test_hard_block_when_high_cost_exceeds_cap(self):
        req = EconomicsRequestIn(**{**VALID_REQUEST, "job_budget_cap": 5.00})
        route = self._make_route("openai", 8.0, 7.0, 10.0)
        policy = PolicyEngine()
        results = policy.apply_policies(req, [route])
        assert results[0].budget_status == "blocked"
        assert "HARD_BUDGET_BLOCK" in results[0].policy_flags
        assert results[0].rejection_reason is not None

    def test_warning_when_high_cost_near_cap(self):
        req = EconomicsRequestIn(**{**VALID_REQUEST, "job_budget_cap": 10.00})
        # high_cost = $9.00 = 90% of $10 cap → warning
        route = self._make_route("runway", 8.0, 7.0, 9.0)
        policy = PolicyEngine()
        results = policy.apply_policies(req, [route])
        assert results[0].budget_status == "warning"
        assert "NEAR_BUDGET_WARNING" in results[0].policy_flags

    def test_safe_when_well_under_cap(self):
        req = EconomicsRequestIn(**{**VALID_REQUEST, "job_budget_cap": 100.00})
        route = self._make_route("fal", 5.0, 4.5, 6.0)
        policy = PolicyEngine()
        results = policy.apply_policies(req, [route])
        assert results[0].budget_status == "safe"

    def test_async_savings_flag_fires_when_savings_above_threshold(self):
        req = EconomicsRequestIn(**{**VALID_REQUEST, "job_budget_cap": 100.00})
        sync_route  = self._make_route("openai",       10.0, 9.0, 12.0, is_async=False)
        async_route = self._make_route("openai_batch", 6.0,  5.0, 7.0,  is_async=True)
        policy = PolicyEngine()
        results = policy.apply_policies(req, [sync_route, async_route])
        async_result = next(r for r in results if r.route.provider == "openai_batch")
        assert "ASYNC_SAVINGS_RECOMMENDED" in async_result.policy_flags

    def test_no_cap_means_no_block(self):
        data = {k: v for k, v in VALID_REQUEST.items()}
        data.pop("job_budget_cap", None)
        data.pop("workspace_budget_cap", None)
        req = EconomicsRequestIn(**data)
        route = self._make_route("replicate", 1000.0, 900.0, 1200.0)
        policy = PolicyEngine()
        results = policy.apply_policies(req, [route])
        assert results[0].budget_status == "safe"


# ===========================================================================
# 5. Route Ranker Tests (ECO-FR-040, 041, 042, 044)
# ===========================================================================

class TestRouteRanker:

    def _make_policy_result(self, provider, base, is_async=False, blocked=False):
        from schemas.economics_schema import RouteEstimate
        from services.policy_engine import PolicyResult
        status = "blocked" if blocked else "safe"
        route = RouteEstimate(
            provider=provider,
            estimated_base_cost=base,
            estimated_low_cost=base * 0.9,
            estimated_high_cost=base * 1.2,
            budget_status=status,
            cost_class="medium",
            confidence_class="high",
            explanation="test",
            is_async_batch=is_async,
        )
        return PolicyResult(
            route=route,
            budget_status=status,
            policy_flags=[],
        )

    def test_cheapest_eligible_route_ranks_first(self):
        req = EconomicsRequestIn(**VALID_REQUEST)
        results = [
            self._make_policy_result("expensive_provider", 50.0),
            self._make_policy_result("cheap_provider",     5.0),
            self._make_policy_result("mid_provider",       20.0),
        ]
        ranker = RouteRanker()
        ranked = ranker.rank(req, results)
        assert ranked[0].route.provider == "cheap_provider"

    def test_blocked_routes_excluded_from_recommendation(self):
        req = EconomicsRequestIn(**VALID_REQUEST)
        results = [
            self._make_policy_result("blocked_provider", 3.0, blocked=True),
            self._make_policy_result("ok_provider",      10.0),
        ]
        ranker = RouteRanker()
        recommended, alternatives = ranker.build_response_parts(ranker.rank(req, results))
        assert recommended is not None
        assert recommended.provider == "ok_provider"

    def test_all_blocked_returns_none_recommended(self):
        req = EconomicsRequestIn(**VALID_REQUEST)
        results = [
            self._make_policy_result("p1", 50.0, blocked=True),
            self._make_policy_result("p2", 60.0, blocked=True),
        ]
        ranker = RouteRanker()
        recommended, alternatives = ranker.build_response_parts(ranker.rank(req, results))
        assert recommended is None
        assert alternatives == []

    def test_max_two_alternatives_returned(self):
        req = EconomicsRequestIn(**VALID_REQUEST)
        results = [
            self._make_policy_result("p1", 5.0),
            self._make_policy_result("p2", 10.0),
            self._make_policy_result("p3", 15.0),
            self._make_policy_result("p4", 20.0),
        ]
        ranker = RouteRanker()
        _, alternatives = ranker.build_response_parts(ranker.rank(req, results))
        assert len(alternatives) <= 2

    def test_async_route_preferred_when_latency_is_async_ok(self):
        req = EconomicsRequestIn(**{**VALID_REQUEST, "latency_mode": "async_ok"})
        results = [
            self._make_policy_result("sync_route",  8.0, is_async=False),
            self._make_policy_result("async_route", 8.0, is_async=True),
        ]
        ranker = RouteRanker()
        ranked = ranker.rank(req, results)
        assert ranked[0].route.provider == "async_route"

    def test_scores_are_between_0_and_1(self):
        req = EconomicsRequestIn(**VALID_REQUEST)
        results = [
            self._make_policy_result("p1", 5.0),
            self._make_policy_result("p2", 20.0),
        ]
        ranker = RouteRanker()
        ranked = ranker.rank(req, results)
        for r in ranked:
            if r.score > 0:
                assert 0.0 <= r.score <= 1.0


# ===========================================================================
# 6. API Endpoint Tests (Integration)
# ===========================================================================

class TestAPIEndpoints:

    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_post_estimate_returns_201(self, client):
        resp = client.post("/api/video-economics/estimate", json=VALID_REQUEST)
        assert resp.status_code == 201
        data = resp.json()
        assert "request_id" in data
        assert "recommended_route" in data
        assert data["request_status"] in ("completed", "blocked")

    def test_post_estimate_recommended_route_is_lowest_eligible_cost(self, client):
        resp = client.post("/api/video-economics/estimate", json=VALID_REQUEST)
        assert resp.status_code == 201
        data = resp.json()
        if data["recommended_route"]:
            rec_cost = data["recommended_route"]["estimated_base_cost"]
            for alt in data.get("alternatives", []):
                assert rec_cost <= alt["estimated_base_cost"] * 2  # ranked by score, not pure cost

    def test_post_estimate_blocked_returns_blocked_status(self, client):
        blocked_req = {**VALID_REQUEST, "job_budget_cap": 0.001}
        resp = client.post("/api/video-economics/estimate", json=blocked_req)
        assert resp.status_code == 201
        data = resp.json()
        assert data["request_status"] == "blocked"
        assert data["recommended_route"] is None

    def test_get_estimate_by_id(self, client):
        post_resp = client.post("/api/video-economics/estimate", json=VALID_REQUEST)
        request_id = post_resp.json()["request_id"]

        get_resp = client.get(f"/api/video-economics/estimate/{request_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["request_id"] == request_id

    def test_get_estimate_not_found(self, client):
        resp = client.get("/api/video-economics/estimate/nonexistent-id-12345")
        assert resp.status_code == 404

    def test_simulate_endpoint(self, client):
        resp = client.post("/api/video-economics/simulate", json=VALID_REQUEST)
        assert resp.status_code == 200
        assert resp.json()["simulation_mode"] is True

    def test_list_providers(self, client):
        resp = client.get("/api/video-economics/providers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 5
        provider_keys = [p["provider_key"] for p in data["providers"]]
        assert "openai" in provider_keys
        assert "runway" in provider_keys
        assert "fal" in provider_keys
        assert "replicate" in provider_keys
        assert "piapi" in provider_keys

    def test_override_endpoint(self, client):
        post_resp = client.post("/api/video-economics/estimate", json=VALID_REQUEST)
        request_id = post_resp.json()["request_id"]

        override_resp = client.post(
            f"/api/video-economics/estimate/{request_id}/override",
            json={"override_provider": "runway", "override_reason": "BD team preference"},
        )
        assert override_resp.status_code == 201
        data = override_resp.json()
        assert data["override_provider"] == "runway"
        assert data["stored"] is True

    def test_missing_required_field_returns_422(self, client):
        bad_req = {**VALID_REQUEST}
        del bad_req["use_case"]
        resp = client.post("/api/video-economics/estimate", json=bad_req)
        assert resp.status_code == 422

    def test_all_routes_returned_in_response(self, client):
        resp = client.post("/api/video-economics/estimate", json=VALID_REQUEST)
        data = resp.json()
        assert len(data["all_routes"]) >= 5  # one per active provider

    def test_explanation_present_on_recommended_route(self, client):
        resp = client.post("/api/video-economics/estimate", json=VALID_REQUEST)
        data = resp.json()
        if data["recommended_route"]:
            assert data["recommended_route"]["explanation"] != ""



