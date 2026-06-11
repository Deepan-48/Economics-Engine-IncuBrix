"""
services_v2/decision/route_decision_service.py
"""
from __future__ import annotations
from typing import Optional
from schemas_v2.economics_v2_schema import EstimateResultV2, EstimateRequestV2, LatencyMode

WEIGHTS = {"cost_fit": 0.40, "budget_safety": 0.20, "latency_fit": 0.15,
           "quality_aff": 0.10, "confidence": 0.10, "margin_safety": 0.05}

BLOCKED = {"blocked_hard_cap", "blocked_margin"}


def _cost_fit(r, eligible):
    costs = [e.estimated_base_cost for e in eligible]
    mn, mx = min(costs), max(costs)
    return 1.0 if mx == mn else (mx - r.estimated_base_cost) / (mx - mn)

def _budget_safety(r, cap):
    if cap is None: return 0.8
    return max(0.0, min(1.0, (cap - r.estimated_high_cost) / cap))

def _latency_fit(r, mode):
    if mode == LatencyMode.async_ok: return 1.0 if r.is_async_batch else 0.6
    if mode == LatencyMode.fastest: return 0.3 if r.is_async_batch else 1.0
    return 0.7

def _quality_aff(r):
    return {"low": 1.0, "medium": 0.6, "high": 0.3}.get(r.cost_class, 0.5)

def _confidence(r):
    return {"high": 1.0, "medium": 0.6, "low": 0.3}.get(r.confidence_class, 0.5)

def _margin_safety(r):
    return 1.0 if r.margin_status == "safe" else 0.0


class RouteDecisionServiceV2:

    def rank(self, request: EstimateRequestV2, estimates: list[EstimateResultV2]) -> list[EstimateResultV2]:
        eligible = [e for e in estimates if e.budget_status not in BLOCKED and e.margin_status != "blocked_margin"]
        blocked  = [e for e in estimates if e.budget_status in BLOCKED or e.margin_status == "blocked_margin"]
        cap = request.job_budget_cap or request.workspace_budget_cap or request.campaign_budget_cap

        scored = []
        for e in eligible:
            score = (
                WEIGHTS["cost_fit"]      * _cost_fit(e, eligible)
                + WEIGHTS["budget_safety"] * _budget_safety(e, cap)
                + WEIGHTS["latency_fit"]   * _latency_fit(e, request.latency_mode)
                + WEIGHTS["quality_aff"]   * _quality_aff(e)
                + WEIGHTS["confidence"]    * _confidence(e)
                + WEIGHTS["margin_safety"] * _margin_safety(e)
            )
            scored.append((round(score, 4), e))

        scored.sort(key=lambda x: x[0], reverse=True)
        result = [e.model_copy(update={"final_score": s}) for s, e in scored]
        result += [e.model_copy(update={"final_score": 0.0}) for e in blocked]
        return result

    def build_response(self, ranked):
        eligible = [e for e in ranked if e.budget_status not in BLOCKED and e.margin_status != "blocked_margin"]
        blocked  = [e for e in ranked if e.budget_status in BLOCKED or e.margin_status == "blocked_margin"]
        recommended  = eligible[0] if eligible else None
        alternatives = eligible[1:3]
        return recommended, alternatives, blocked
