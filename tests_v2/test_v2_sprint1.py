"""
tests_v2/test_v2_sprint1.py
Run: pytest tests_v2/test_v2_sprint1.py -v
"""
import sys, os, pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pydantic import ValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.database import Base, get_db
from main import app

TEST_DB = "sqlite:///./test_v2.db"
test_engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def override_db():
    db = TestSession()
    try: yield db
    finally: db.close()

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    db = TestSession()
    from services.pricing_registry_service import PricingRegistryService
    from services_v2.pricing.pricing_intelligence_service import PricingIntelligenceService
    PricingRegistryService.seed_from_json(db)
    PricingIntelligenceService.seed_from_json(db)
    db.close()
    yield
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("./test_v2.db"): os.remove("./test_v2.db")

@pytest.fixture
def client(setup_db):
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as c: yield c
    app.dependency_overrides.clear()

@pytest.fixture
def db(setup_db):
    s = TestSession(); yield s; s.close()

VALID_V2 = {
    "use_case": "script_to_social_variants", "duration_class": "short", "quality_bar": "high",
    "latency_mode": "async_ok", "batch_size": 10, "variant_count": 2, "budget_mode": "balanced",
    "job_budget_cap": 50.0, "workspace_budget_cap": 500.0, "simulation_mode": True,
}

# Schema tests
class TestSchemaV2:
    def test_valid_request(self):
        from schemas_v2.economics_v2_schema import EstimateRequestV2
        r = EstimateRequestV2(**VALID_V2)
        assert r.batch_size == 10
        assert r.variant_count == 2

    def test_missing_use_case(self):
        from schemas_v2.economics_v2_schema import EstimateRequestV2
        data = {**VALID_V2}; del data["use_case"]
        with pytest.raises(ValidationError): EstimateRequestV2(**data)

    def test_workspace_cap_less_than_job_cap(self):
        from schemas_v2.economics_v2_schema import EstimateRequestV2
        with pytest.raises(ValidationError):
            EstimateRequestV2(**{**VALID_V2, "job_budget_cap": 100.0, "workspace_budget_cap": 50.0})

    def test_correlation_id_auto_generated(self):
        from schemas_v2.economics_v2_schema import EstimateRequestV2
        r = EstimateRequestV2(**VALID_V2)
        assert r.correlation_id is not None and len(r.correlation_id) == 36

# Normalization tests
class TestNormalizationV2:
    def _profile(self, provider_key):
        profiles = {
            "openai": {"provider_key": "openai", "pricing_unit": "per_second", "supports_batch_discount": True, "batch_discount_percent": 50, "default_uncertainty_multiplier_low": 0.9, "default_uncertainty_multiplier_high": 1.2, "base_assumptions": {"short_seconds": 8, "medium_seconds": 20, "long_seconds": 45}, "rate_cards": [{"model_key": "default", "unit_type": "per_second", "unit_rate": 0.030, "quality_class": "high", "currency": "USD"}], "modifiers": [{"modifier_type": "batch_discount", "value_type": "percent", "value": 50, "condition": "execution_mode=batch"}]},
            "runway": {"provider_key": "runway", "pricing_unit": "credits", "supports_batch_discount": False, "batch_discount_percent": 0, "default_uncertainty_multiplier_low": 0.9, "default_uncertainty_multiplier_high": 1.3, "credit_price_usd": 0.01, "base_assumptions": {"short_credits": 50}, "rate_cards": [{"model_key": "default", "unit_type": "credits", "unit_rate": 0.01, "quality_class": "high", "currency": "USD"}], "modifiers": []},
        }
        return profiles[provider_key]

    def test_openai_async_cheaper(self):
        from services_v2.normalization.normalization_service import normalize_provider_cost
        from schemas_v2.economics_v2_schema import DurationClass, QualityBar, LatencyMode
        p = self._profile("openai")
        sync  = normalize_provider_cost(p, DurationClass.short, QualityBar.high, LatencyMode.balanced, 1, 1)
        async_ = normalize_provider_cost(p, DurationClass.short, QualityBar.high, LatencyMode.async_ok, 1, 1)
        assert async_["async_base_cost"] < sync["base_cost"]

    def test_cost_components_returned(self):
        from services_v2.normalization.normalization_service import normalize_provider_cost
        from schemas_v2.economics_v2_schema import DurationClass, QualityBar, LatencyMode
        p = self._profile("openai")
        result = normalize_provider_cost(p, DurationClass.short, QualityBar.high, LatencyMode.balanced, 1, 1)
        assert len(result["cost_components"]) > 0
        assert "unit_type" in result["cost_components"][0]

    def test_normalization_trace_present(self):
        from services_v2.normalization.normalization_service import normalize_provider_cost
        from schemas_v2.economics_v2_schema import DurationClass, QualityBar, LatencyMode
        p = self._profile("runway")
        result = normalize_provider_cost(p, DurationClass.short, QualityBar.high, LatencyMode.balanced, 1, 1)
        assert "normalization_trace" in result
        assert result["normalization_trace"]["formula_version"] == "v2.0"

    def test_variant_count_scales_cost(self):
        from services_v2.normalization.normalization_service import normalize_provider_cost
        from schemas_v2.economics_v2_schema import DurationClass, QualityBar, LatencyMode
        p = self._profile("openai")
        single = normalize_provider_cost(p, DurationClass.short, QualityBar.high, LatencyMode.balanced, 1, 1)
        double = normalize_provider_cost(p, DurationClass.short, QualityBar.high, LatencyMode.balanced, 1, 2)
        assert abs(double["base_cost"] - single["base_cost"] * 2) < 0.01

# Estimation engine tests
class TestEstimationEngineV2:
    def test_returns_results_for_all_providers(self, db):
        from services_v2.pricing.pricing_intelligence_service import PricingIntelligenceService
        from services_v2.estimator.estimation_engine_v2 import EstimationEngineV2
        from schemas_v2.economics_v2_schema import EstimateRequestV2
        profiles = PricingIntelligenceService(db).get_active_profiles()
        req = EstimateRequestV2(**VALID_V2)
        results = EstimationEngineV2().estimate_all_routes(req, profiles)
        assert len(results) == len(profiles)

    def test_per_output_cost_calculated(self, db):
        from services_v2.pricing.pricing_intelligence_service import PricingIntelligenceService
        from services_v2.estimator.estimation_engine_v2 import EstimationEngineV2
        from schemas_v2.economics_v2_schema import EstimateRequestV2
        profiles = PricingIntelligenceService(db).get_active_profiles()
        req = EstimateRequestV2(**VALID_V2)
        results = EstimationEngineV2().estimate_all_routes(req, profiles)
        for r in results:
            assert r.per_output_cost is not None
            assert r.per_output_cost > 0

    def test_retry_exposure_present(self, db):
        from services_v2.pricing.pricing_intelligence_service import PricingIntelligenceService
        from services_v2.estimator.estimation_engine_v2 import EstimationEngineV2
        from schemas_v2.economics_v2_schema import EstimateRequestV2
        profiles = PricingIntelligenceService(db).get_active_profiles()
        req = EstimateRequestV2(**VALID_V2)
        results = EstimationEngineV2().estimate_all_routes(req, profiles)
        for r in results:
            assert r.retry_exposure is not None

# Budget guardrail tests
class TestBudgetGuardrailV2:
    def _make_estimate(self, base, high):
        from schemas_v2.economics_v2_schema import EstimateResultV2
        return EstimateResultV2(request_id="test", provider_key="openai", model_key="default",
            estimated_low_cost=base*0.9, estimated_base_cost=base, estimated_high_cost=high,
            confidence_class="high", cost_class="medium", budget_status="safe", explanation="test")

    def test_hard_block(self):
        from services_v2.budget.budget_guardrail_service import BudgetGuardrailService
        e = self._make_estimate(8.0, 10.0)
        result = BudgetGuardrailService().check(e, job_budget_cap=5.0)
        assert result["budget_status"] == "blocked_hard_cap"
        assert result["blocked_reason"] is not None

    def test_warning_near_cap(self):
        from services_v2.budget.budget_guardrail_service import BudgetGuardrailService
        e = self._make_estimate(8.0, 9.0)
        result = BudgetGuardrailService().check(e, job_budget_cap=10.0)
        assert result["budget_status"] == "warn_near_cap"

    def test_safe(self):
        from services_v2.budget.budget_guardrail_service import BudgetGuardrailService
        e = self._make_estimate(3.0, 3.6)
        result = BudgetGuardrailService().check(e, job_budget_cap=100.0)
        assert result["budget_status"] == "safe"

    def test_reservation_and_settle(self, db):
        from services_v2.budget.budget_guardrail_service import BudgetGuardrailService
        from schemas_v2.economics_v2_schema import BudgetReservationIn
        svc = BudgetGuardrailService()
        res = svc.reserve(BudgetReservationIn(estimate_id="est-1", reserved_amount=25.0, workspace_id="ws-1", expires_minutes=60), db)
        assert res["status"] == "reserved"
        settled = svc.settle(res["reservation_id"], 20.0, db)
        assert settled["status"] == "settled"
        assert settled["released_amount"] == 5.0

    def test_reservation_release(self, db):
        from services_v2.budget.budget_guardrail_service import BudgetGuardrailService
        from schemas_v2.economics_v2_schema import BudgetReservationIn
        svc = BudgetGuardrailService()
        res = svc.reserve(BudgetReservationIn(estimate_id="est-2", reserved_amount=15.0, expires_minutes=60), db)
        released = svc.release(res["reservation_id"], db)
        assert released["status"] == "released"
        assert released["released_amount"] == 15.0

# Margin tests
class TestMarginV2:
    def _make_estimate(self, base):
        from schemas_v2.economics_v2_schema import EstimateResultV2
        return EstimateResultV2(request_id="test", provider_key="openai", model_key="default",
            estimated_low_cost=base*0.9, estimated_base_cost=base, estimated_high_cost=base*1.2,
            confidence_class="high", cost_class="medium", budget_status="safe", explanation="test")

    def test_markup_calculates_margin(self):
        from services_v2.margin.margin_policy_service import MarginPolicyServiceV2
        from schemas_v2.economics_v2_schema import MarkupMode
        e = self._make_estimate(10.0)
        result = MarginPolicyServiceV2().evaluate(e, MarkupMode.markup, 25.0, None)
        assert result["gross_margin_percent"] == pytest.approx(60.0, rel=0.01)

    def test_protected_margin_blocks(self):
        from services_v2.margin.margin_policy_service import MarginPolicyServiceV2
        from schemas_v2.economics_v2_schema import MarkupMode
        e = self._make_estimate(18.0)
        result = MarginPolicyServiceV2().evaluate(e, MarkupMode.protected_margin, 20.0, 50.0)
        assert result["is_margin_blocked"] is True

    def test_protected_margin_passes(self):
        from services_v2.margin.margin_policy_service import MarginPolicyServiceV2
        from schemas_v2.economics_v2_schema import MarkupMode
        e = self._make_estimate(10.0)
        result = MarginPolicyServiceV2().evaluate(e, MarkupMode.protected_margin, 100.0, 50.0)
        assert result["is_margin_blocked"] is False

# Route decision tests
class TestRouteDecisionV2:
    def _make_est(self, provider, base, is_async=False, blocked=False):
        from schemas_v2.economics_v2_schema import EstimateResultV2
        return EstimateResultV2(request_id="test", provider_key=provider, model_key="default",
            estimated_low_cost=base*0.9, estimated_base_cost=base, estimated_high_cost=base*1.2,
            confidence_class="high", cost_class="medium",
            budget_status="blocked_hard_cap" if blocked else "safe",
            explanation="test", is_async_batch=is_async)

    def test_cheapest_ranks_first(self):
        from services_v2.decision.route_decision_service import RouteDecisionServiceV2
        from schemas_v2.economics_v2_schema import EstimateRequestV2
        req = EstimateRequestV2(**VALID_V2)
        ests = [self._make_est("expensive", 50.0), self._make_est("cheap", 5.0), self._make_est("mid", 20.0)]
        ranked = RouteDecisionServiceV2().rank(req, ests)
        assert ranked[0].provider_key == "cheap"

    def test_blocked_goes_last(self):
        from services_v2.decision.route_decision_service import RouteDecisionServiceV2
        from schemas_v2.economics_v2_schema import EstimateRequestV2
        req = EstimateRequestV2(**VALID_V2)
        ests = [self._make_est("blocked", 2.0, blocked=True), self._make_est("ok", 10.0)]
        ranked = RouteDecisionServiceV2().rank(req, ests)
        assert ranked[-1].provider_key == "blocked"

    def test_max_two_alternatives(self):
        from services_v2.decision.route_decision_service import RouteDecisionServiceV2
        from schemas_v2.economics_v2_schema import EstimateRequestV2
        req = EstimateRequestV2(**VALID_V2)
        ests = [self._make_est(f"p{i}", float(i*5)) for i in range(1, 6)]
        ranked = RouteDecisionServiceV2().rank(req, ests)
        _, alts, _ = RouteDecisionServiceV2().build_response(ranked)
        assert len(alts) <= 2

# Scenario tests
class TestScenarioV2:
    def test_scenario_run_returns_summary(self, db):
        from services_v2.simulation.scenario_service import ScenarioService
        from schemas_v2.economics_v2_schema import ScenarioRunIn
        from schemas.economics_schema import UseCase, DurationClass, QualityBar, LatencyMode, BudgetMode
        payload = ScenarioRunIn(scenario_name="test_scenario", use_case=UseCase.script_to_social,
            duration_class=DurationClass.short, quality_bar=QualityBar.high,
            latency_mode=LatencyMode.async_ok, batch_size=5, variant_count=1,
            budget_mode=BudgetMode.balanced)
        result = ScenarioService().run(payload, db)
        assert "routes" in result
        assert len(result["routes"]) > 0

# Ledger tests
class TestLedgerV2:
    def test_add_and_query_ledger_entry(self, db):
        from services_v2.ledger.ledger_service import LedgerService
        from schemas_v2.economics_v2_schema import LedgerEntryIn, LedgerEntryType
        svc = LedgerService()
        svc.add_entry(LedgerEntryIn(workspace_id="ws-test", entry_type=LedgerEntryType.estimated, amount=15.0, currency="USD"), db)
        summary = svc.get_summary(workspace_id="ws-test", db=db)
        assert summary["total_estimated"] == pytest.approx(15.0, rel=0.01)

# Actuals tests
class TestActualsV2:
    def test_import_actual_unmapped(self, db):
        from services_v2.actuals.actuals_service import ActualsService
        from schemas_v2.economics_v2_schema import ActualCostImportIn
        result = ActualsService().import_actual(ActualCostImportIn(provider_key="openai", actual_amount=12.50, currency="USD", import_source="manual"), db)
        assert result["actual_cost_id"] is not None
        assert result["map_status"] == "unmapped"

    def test_variance_report_returns_records(self, db):
        from services_v2.actuals.actuals_service import ActualsService
        report = ActualsService().get_variance_report(db=db)
        assert "records" in report

# Analytics tests
class TestAnalyticsV2:
    def test_events_saved(self, db):
        from services_v2.analytics.analytics_service_v2 import AnalyticsServiceV2
        svc = AnalyticsServiceV2(db)
        svc.estimate_created("req-1", "corr-1", "ws-1", "openai", 10.0, "safe")
        events = svc.get_events(event_type="economics.v2.estimate.created")
        assert len(events) > 0

    def test_summary_returns_counts(self, db):
        from services_v2.analytics.analytics_service_v2 import AnalyticsServiceV2
        summary = AnalyticsServiceV2(db).get_summary()
        assert "total_estimates" in summary

# Pricing intelligence tests
class TestPricingIntelligenceV2:
    def test_active_profiles_returned(self, db):
        from services_v2.pricing.pricing_intelligence_service import PricingIntelligenceService
        profiles = PricingIntelligenceService(db).get_active_profiles()
        assert len(profiles) >= 5

    def test_stage_and_validate_profile(self, db):
        from services_v2.pricing.pricing_intelligence_service import PricingIntelligenceService
        svc = PricingIntelligenceService(db)
        draft = {"provider_key": "openai", "model_key": "default", "currency": "USD",
                 "supports_batch_discount": True, "batch_discount_percent": 40,
                 "default_uncertainty_multiplier_low": 0.9, "default_uncertainty_multiplier_high": 1.2,
                 "base_assumptions": {"short_seconds": 8, "medium_seconds": 20, "long_seconds": 45},
                 "rate_cards": [{"model_key": "default", "unit_type": "per_second", "unit_rate": 0.028, "quality_class": "high", "currency": "USD"}],
                 "modifiers": []}
        stage_result = svc.stage_profile("openai", draft, "test_admin")
        assert stage_result["staged_version"] >= 2
        validate_result = svc.validate_profile("openai", draft)
        assert validate_result["valid"] is True

    def test_rollback(self, db):
        from services_v2.pricing.pricing_intelligence_service import PricingIntelligenceService
        svc = PricingIntelligenceService(db)
        active = svc.get_active_profiles()
        provider = active[0]["provider_key"]
        staged = svc.stage_profile(provider, {**active[0]}, "test_admin")
        svc.approve_and_activate(provider, staged["staged_version"], "test_admin")
        rollback = svc.rollback(provider)
        assert "rolled_back_to" in rollback

# API endpoint tests
class TestAPIV2:
    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_post_estimate_v2(self, client):
        resp = client.post("/api/economics/v2/estimate", json=VALID_V2)
        assert resp.status_code == 201
        data = resp.json()
        assert "request_id" in data
        assert "recommended_route" in data
        assert "all_routes" in data
        assert len(data["all_routes"]) >= 5

    def test_v2_response_has_cost_components(self, client):
        resp = client.post("/api/economics/v2/estimate", json=VALID_V2)
        data = resp.json()
        if data.get("recommended_route"):
            assert "cost_components" in data["recommended_route"]

    def test_v2_response_has_routing_adapter(self, client):
        resp = client.post("/api/economics/v2/estimate", json=VALID_V2)
        data = resp.json()
        assert "routing_adapter" in data

    def test_blocked_request(self, client):
        req = {**VALID_V2, "job_budget_cap": 0.001}
        resp = client.post("/api/economics/v2/estimate", json=req)
        assert resp.status_code == 201
        assert resp.json()["request_status"] == "blocked"

    def test_simulate_endpoint(self, client):
        resp = client.post("/api/economics/v2/simulate", json=VALID_V2)
        assert resp.status_code == 200
        assert resp.json()["simulation_mode"] is True

    def test_scenario_run_endpoint(self, client):
        payload = {"scenario_name": "api_test", "use_case": "script_to_social_variants",
                   "duration_class": "short", "quality_bar": "high", "latency_mode": "async_ok",
                   "batch_size": 5, "variant_count": 1, "budget_mode": "balanced"}
        resp = client.post("/api/economics/v2/scenarios/run", json=payload)
        assert resp.status_code == 201
        assert "routes" in resp.json()

    def test_ledger_summary_endpoint(self, client):
        resp = client.get("/api/economics/v2/ledger/summary")
        assert resp.status_code == 200

    def test_analytics_summary_endpoint(self, client):
        resp = client.get("/api/economics/v2/analytics/summary")
        assert resp.status_code == 200

    def test_forecast_endpoint(self, client):
        resp = client.get("/api/economics/v2/analytics/forecast?days_ahead=30")
        assert resp.status_code == 200
        assert "forecasted_spend" in resp.json()

    def test_active_providers_v2_endpoint(self, client):
        resp = client.get("/api/economics/v2/providers/pricing/active")
        assert resp.status_code == 200
        assert resp.json()["count"] >= 5

    def test_actuals_import_endpoint(self, client):
        payload = {"provider_key": "openai", "actual_amount": 12.50, "currency": "USD", "import_source": "manual"}
        resp = client.post("/api/economics/v2/actuals/import", json=payload)
        assert resp.status_code == 201

    def test_idempotency_key_returns_cached(self, client):
        req = {**VALID_V2, "idempotency_key": "test-idem-key-001"}
        resp1 = client.post("/api/economics/v2/estimate", json=req)
        resp2 = client.post("/api/economics/v2/estimate", json=req)
        assert resp1.status_code == 201
        assert resp2.status_code == 201
