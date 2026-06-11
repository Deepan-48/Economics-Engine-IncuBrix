"""
services_v2/simulation/scenario_service.py
ECO2-SIM-001 to ECO2-SIM-004
"""
from __future__ import annotations
import uuid, csv, io
from datetime import datetime
from sqlalchemy.orm import Session
from schemas_v2.economics_v2_schema import ScenarioRunIn, EstimateRequestV2
from services_v2.pricing.pricing_intelligence_service import PricingIntelligenceService
from services_v2.estimator.estimation_engine_v2 import EstimationEngineV2
from services_v2.margin.margin_policy_service import MarginPolicyServiceV2
from models_v2.models_v2 import EconomicsScenario


class ScenarioService:

    def run(self, payload: ScenarioRunIn, db: Session) -> dict:
        request = EstimateRequestV2(
            use_case=payload.use_case, duration_class=payload.duration_class,
            quality_bar=payload.quality_bar, latency_mode=payload.latency_mode,
            batch_size=payload.batch_size, variant_count=payload.variant_count,
            budget_mode=payload.budget_mode, job_budget_cap=payload.job_budget_cap,
            price_to_customer=payload.price_to_customer,
            target_margin_percent=payload.target_margin_percent,
            markup_mode=payload.markup_mode, simulation_mode=True,
        )

        profiles = PricingIntelligenceService(db).get_active_profiles()
        estimates = EstimationEngineV2().estimate_all_routes(request, profiles)
        margin_svc = MarginPolicyServiceV2()

        total_outputs = payload.batch_size * payload.variant_count
        route_results = []
        for e in estimates:
            m = margin_svc.evaluate(e, payload.markup_mode, payload.price_to_customer, payload.target_margin_percent)
            route_results.append({
                "provider":         e.provider_key,
                "execution_mode":   e.execution_mode,
                "base_cost":        e.estimated_base_cost,
                "low_cost":         e.estimated_low_cost,
                "high_cost":        e.estimated_high_cost,
                "budget_status":    e.budget_status,
                "confidence_class": e.confidence_class,
                "per_output_cost":  round(e.estimated_base_cost / total_outputs, 4) if total_outputs > 0 else None,
                "gross_margin_pct": m.get("gross_margin_percent"),
                "margin_status":    m.get("margin_status"),
            })

        eligible = [r for r in route_results if r["budget_status"] not in ("blocked_hard_cap", "blocked_margin")]
        total_min = min((r["base_cost"] for r in eligible), default=0)
        total_max = max((r["base_cost"] for r in eligible), default=0)

        summary = {
            "scenario_id":    str(uuid.uuid4()),
            "scenario_name":  payload.scenario_name,
            "total_cost_range": {"min": total_min, "max": total_max},
            "per_output_range": {
                "min": round(total_min / total_outputs, 4) if total_outputs > 0 else None,
                "max": round(total_max / total_outputs, 4) if total_outputs > 0 else None,
            },
            "routes":     route_results,
            "created_at": datetime.utcnow().isoformat(),
        }

        s = EconomicsScenario(
            scenario_name=payload.scenario_name,
            input_config=payload.model_dump(mode="json"),
            result_summary=summary, status="completed",
        )
        db.add(s)
        db.commit()
        summary["scenario_db_id"] = str(s.id)
        return summary

    def get(self, scenario_id: str, db: Session) -> dict:
        s = db.query(EconomicsScenario).filter(EconomicsScenario.id == scenario_id).first()
        if not s:
            return {"error": "Scenario not found."}
        return {"id": str(s.id), "scenario_name": s.scenario_name,
                "status": s.status, "result": s.result_summary,
                "created_at": s.created_at.isoformat()}

    def export_csv(self, scenario_id: str, db: Session) -> str:
        s = db.query(EconomicsScenario).filter(EconomicsScenario.id == scenario_id).first()
        if not s or not s.result_summary:
            return ""
        routes = s.result_summary.get("routes", [])
        output = io.StringIO()
        if not routes:
            return ""
        writer = csv.DictWriter(output, fieldnames=list(routes[0].keys()))
        writer.writeheader()
        writer.writerows(routes)
        return output.getvalue()
