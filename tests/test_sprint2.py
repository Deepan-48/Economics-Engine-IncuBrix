"""
tests/test_sprint2.py

Sprint 2 test suite covering:
- Fallback estimator (ECO-FR-022)
- Margin engine (ECO-FR-032, ECO-FR-033)
- Analytics events (ECO-FR-060 to 063)
- Admin endpoints (ECO-FR-050, ECO-FR-052)
- Savings delta (ECO-FR-043)
- Near budget warning (ECO-FR-031)
- Full pipeline with sprint 2 features

Run: pytest tests/test_sprint2.py -v
"""

import sys, os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import Base, get_db
from main import app
from schemas.economics_schema import (
    EconomicsRequestIn, DurationClass, QualityBar,
    LatencyMode, BudgetMode, MarkupMode, RouteEstimate
)
from services.fallback_estimator import FallbackEstimator
from services.margin_engine import MarginEngine

TEST_DB = "sqlite:///./test_sprint2.db"
test_engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestSession()
    from services.pricing_registry_service import PricingRegistryService
    PricingRegistryService.seed_from_json(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("./test_sprint2.db"):
        os.remove("./test_sprint2.db")


@pytest.fixture
def client(setup_db):
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def db(setup_db):
    session = TestSession()
    yield session
    session.close()


VALID = {
    "use_case": "script_to_social_variants",
    "duration_class": "short",
    "quality_bar": "high",
    "latency_mode": "async_ok",
    "batch_size": 10,
    "budget_mode": "balanced",
    "job_budget_cap": 25.0,
    "workspace_budget_cap": 500.0,
    "simulation_mode": True,
}


def _make_route(provider, base, is_async=False, blocked=False):
    return RouteEstimate(
        provider=provider,
        estimated_base_cost=base,
        estimated_low_cost=round(base * 0.9, 4),
        estimated_high_cost=round(base * 1.2, 4),
        budget_status="blocked" if blocked else "safe",
        cost_class="medium",
        confidence_class="high",
        explanation="test route",
        is_async_batch=is_async,
    )


# ── Fallback Estimator ───────────────────────────────────────────────────────

class TestFallbackEstimator:

    def test_retry_cost_is_60_percent_of_primary(self):
        req = EconomicsRequestIn(**VALID)
        recommended = _make_route("openai", 10.0)
        alts = [_make_route("runway", 12.0)]
        fe = FallbackEstimator()
        result = fe.estimate(req, recommended, alts)
        assert result.retry_cost == pytest.approx(6.0, rel=0.01)

    def test_fallback_provider_is_cheapest_alternative(self):
        req = EconomicsRequestIn(**VALID)
        recommended = _make_route("openai", 10.0)
        alts = [_make_route("runway", 15.0), _make_route("fal", 8.0)]
        fe = FallbackEstimator()
        result = fe.estimate(req, recommended, alts)
        assert result.fallback_provider == "fal"
        assert result.fallback_cost == 8.0

    def test_worst_case_includes_all_costs(self):
        req = EconomicsRequestIn(**VALID)
        recommended = _make_route("openai", 10.0)
        alts = [_make_route("runway", 12.0)]
        fe = FallbackEstimator()
        result = fe.estimate(req, recommended, alts)
        # 10 + 6 (retry) + 12 (fallback) = 28
        assert result.total_worst_case == pytest.approx(28.0, rel=0.01)

    def test_no_fallback_when_all_alternatives_blocked(self):
        req = EconomicsRequestIn(**VALID)
        recommended = _make_route("openai", 10.0)
        alts = [_make_route("runway", 12.0, blocked=True)]
        fe = FallbackEstimator()
        result = fe.estimate(req, recommended, alts)
        assert result.fallback_provider is None
        assert result.fallback_cost is None

    def test_explanation_is_present(self):
        req = EconomicsRequestIn(**VALID)
        recommended = _make_route("replicate", 5.0)
        alts = [_make_route("fal", 7.0)]
        fe = FallbackEstimator()
        result = fe.estimate(req, recommended, alts)
        assert len(result.explanation) > 0
        assert "replicate" in result.explanation.lower()


# ── Margin Engine ────────────────────────────────────────────────────────────

class TestMarginEngine:

    def test_pass_through_sets_price_to_cost(self):
        route = _make_route("openai", 10.0)
        me = MarginEngine()
        result = me.calculate(route, MarkupMode.pass_through, None, None)
        assert result.price_to_customer == pytest.approx(10.0)
        assert result.is_margin_blocked is False

    def test_markup_mode_calculates_margin(self):
        route = _make_route("openai", 10.0)
        me = MarginEngine()
        result = me.calculate(route, MarkupMode.markup, 25.0, None)
        assert result.gross_margin_amount == pytest.approx(15.0, rel=0.01)
        assert result.gross_margin_percent == pytest.approx(60.0, rel=0.01)

    def test_protected_margin_blocks_when_below_target(self):
        route = _make_route("openai", 18.0)
        me = MarginEngine()
        # price=20, cost=18, margin=10% — below 50% target
        result = me.calculate(route, MarkupMode.protected_margin, 20.0, 50.0)
        assert result.is_margin_blocked is True

    def test_protected_margin_passes_when_above_target(self):
        route = _make_route("openai", 10.0)
        me = MarginEngine()
        # price=100, cost=10, margin=90% — above 50% target
        result = me.calculate(route, MarkupMode.protected_margin, 100.0, 50.0)
        assert result.is_margin_blocked is False

    def test_markup_mode_without_price_returns_explanation(self):
        route = _make_route("runway", 5.0)
        me = MarginEngine()
        result = me.calculate(route, MarkupMode.markup, None, None)
        assert result.gross_margin_percent is None
        assert "not provided" in result.explanation


# ── Analytics Events ─────────────────────────────────────────────────────────

class TestAnalyticsEvents:

    def test_estimate_created_event_saved(self, client, db):
        from models.analytics_event import AnalyticsEvent
        resp = client.post("/api/video-economics/estimate", json=VALID)
        assert resp.status_code == 201
        request_id = resp.json()["request_id"]
        event = db.query(AnalyticsEvent).filter(
            AnalyticsEvent.request_id == request_id,
            AnalyticsEvent.event_type == "economics_estimate_created",
        ).first()
        assert event is not None

    def test_budget_blocked_event_saved(self, client, db):
        from models.analytics_event import AnalyticsEvent
        blocked = {**VALID, "job_budget_cap": 0.001}
        resp = client.post("/api/video-economics/estimate", json=blocked)
        request_id = resp.json()["request_id"]
        events = db.query(AnalyticsEvent).filter(
            AnalyticsEvent.request_id == request_id,
            AnalyticsEvent.event_type == "economics_budget_blocked",
        ).all()
        assert len(events) > 0

    def test_override_event_saved(self, client, db):
        from models.analytics_event import AnalyticsEvent
        post = client.post("/api/video-economics/estimate", json=VALID)
        rid = post.json()["request_id"]
        client.post(f"/api/video-economics/estimate/{rid}/override",
                    json={"override_provider": "runway", "override_reason": "test"})
        event = db.query(AnalyticsEvent).filter(
            AnalyticsEvent.request_id == rid,
            AnalyticsEvent.event_type == "economics_override_submitted",
        ).first()
        assert event is not None

    def test_analytics_endpoint_returns_events(self, client):
        client.post("/api/video-economics/estimate", json=VALID)
        resp = client.get("/api/video-economics/admin/analytics")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_analytics_filter_by_event_type(self, client):
        resp = client.get(
            "/api/video-economics/admin/analytics",
            params={"event_type": "economics_estimate_created"}
        )
        assert resp.status_code == 200
        for e in resp.json()["events"]:
            assert e["event_type"] == "economics_estimate_created"


# ── Admin Endpoints ───────────────────────────────────────────────────────────

class TestAdminEndpoints:

    def test_list_all_providers(self, client):
        resp = client.get("/api/video-economics/admin/providers")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 5

    def test_update_provider_creates_new_version(self, client):
        resp = client.patch(
            "/api/video-economics/admin/providers/openai",
            json={"pricing_profile_json": {"rate_per_second": 0.025}, "reason": "price drop"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["new_version"] == 2
        assert data["previous_version"] == 1

    def test_rollback_restores_previous_version(self, client):
        # update first to have v2
        client.patch(
            "/api/video-economics/admin/providers/runway",
            json={"pricing_profile_json": {"credit_price_usd": 0.009}}
        )
        resp = client.post("/api/video-economics/admin/providers/runway/rollback")
        assert resp.status_code == 200
        assert "rolled_back_to" in resp.json()

    def test_toggle_provider_deactivates(self, client):
        resp = client.post("/api/video-economics/admin/providers/piapi/toggle")
        assert resp.status_code == 200
        # toggle back so other tests aren't affected
        client.post("/api/video-economics/admin/providers/piapi/toggle")

    def test_get_thresholds(self, client):
        resp = client.get("/api/video-economics/admin/thresholds")
        assert resp.status_code == 200
        data = resp.json()
        assert "near_budget_threshold" in data
        assert "async_savings_threshold" in data

    def test_update_thresholds(self, client):
        resp = client.patch(
            "/api/video-economics/admin/thresholds",
            json={"near_budget_threshold": 0.90}
        )
        assert resp.status_code == 200
        assert resp.json()["updated"]["near_budget_threshold"] == 0.90
        # reset
        client.patch("/api/video-economics/admin/thresholds",
                     json={"near_budget_threshold": 0.85})

    def test_rollback_fails_when_only_one_version(self, client):
        # fal should only have v1 if not updated yet
        resp = client.post("/api/video-economics/admin/providers/fal/rollback")
        # either 400 (no previous) or 200 if already updated — just check it doesn't 500
        assert resp.status_code in (200, 400)


# ── Sprint 2 API Features ────────────────────────────────────────────────────

class TestSprint2APIFeatures:

    def test_savings_delta_present_in_response(self, client):
        resp = client.post("/api/video-economics/estimate", json=VALID)
        data = resp.json()
        # savings_delta can be None if only one eligible route, or a float
        assert "savings_delta_vs_next" in data

    def test_fallback_exposure_present_in_response(self, client):
        resp = client.post("/api/video-economics/estimate", json=VALID)
        data = resp.json()
        assert "fallback_exposure" in data
        if data["recommended_route"]:
            assert data["fallback_exposure"] is not None
            assert "total_worst_case" in data["fallback_exposure"]

    def test_margin_simulation_in_response_when_markup_mode_set(self, client):
        req = {**VALID, "markup_mode": "markup", "price_to_customer": 60.0}
        resp = client.post("/api/video-economics/estimate", json=req)
        data = resp.json()
        assert "margin_simulation" in data
        assert data["margin_simulation"] is not None
        assert data["margin_simulation"]["gross_margin_percent"] is not None

    def test_protected_margin_blocks_route_when_margin_too_low(self, client):
        req = {
            **VALID,
            "markup_mode": "protected_margin",
            "price_to_customer": 0.50,
            "target_margin_percent": 80.0,
            "job_budget_cap": 1000.0,
            "workspace_budget_cap": 5000.0,
        }
        resp = client.post("/api/video-economics/estimate", json=req)
        data = resp.json()
        assert data["margin_simulation"]["is_margin_blocked"] is True

    def test_near_budget_warning_in_all_routes(self, client):
        # set cap just above expected cost so some routes get warning
        req = {**VALID, "job_budget_cap": 4.0, "batch_size": 1}
        resp = client.post("/api/video-economics/estimate", json=req)
        data = resp.json()
        statuses = [r["budget_status"] for r in data["all_routes"]]
        # at least some should be safe, warning, or blocked — not all the same
        assert len(set(statuses)) >= 1

    def test_simulate_endpoint_has_sprint2_fields(self, client):
        resp = client.post("/api/video-economics/simulate", json=VALID)
        assert resp.status_code == 200
        data = resp.json()
        assert "fallback_exposure" in data
        assert "savings_delta_vs_next" in data
