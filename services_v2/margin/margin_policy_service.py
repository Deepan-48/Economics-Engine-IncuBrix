"""
services_v2/margin/margin_policy_service.py
ECO2-MAR-001 to ECO2-MAR-003
"""
from __future__ import annotations
from typing import Optional
from schemas_v2.economics_v2_schema import EstimateResultV2, MarkupMode


class MarginPolicyServiceV2:

    def evaluate(self, estimate: EstimateResultV2, markup_mode: Optional[MarkupMode],
                 price_to_customer: Optional[float], target_margin_percent: Optional[float]) -> dict:
        base = estimate.estimated_base_cost
        mode = markup_mode.value if markup_mode else "pass_through"
        is_blocked = False
        margin_amount = None
        margin_pct = None

        if mode == "pass_through":
            effective_price = base
            margin_amount = 0.0
            margin_pct = 0.0
            explanation = f"Pass-through: customer pays ${base:.2f}."

        elif mode == "markup":
            effective_price = price_to_customer
            if price_to_customer and price_to_customer > base:
                margin_amount = round(price_to_customer - base, 4)
                margin_pct = round((margin_amount / price_to_customer) * 100, 2)
                explanation = f"Markup: cost ${base:.2f}, price ${price_to_customer:.2f}, margin {margin_pct:.1f}%."
            else:
                explanation = "Markup: price_to_customer not set or below cost."

        elif mode == "protected_margin":
            effective_price = price_to_customer
            if price_to_customer and price_to_customer > 0:
                margin_amount = round(price_to_customer - base, 4)
                margin_pct = round((margin_amount / price_to_customer) * 100, 2)
                if target_margin_percent and margin_pct < target_margin_percent:
                    is_blocked = True
                    explanation = f"Protected margin: {margin_pct:.1f}% below target {target_margin_percent:.1f}%. Blocked."
                else:
                    explanation = f"Protected margin: {margin_pct:.1f}% meets target {target_margin_percent or 0:.1f}%."
            else:
                explanation = "Protected margin requires price_to_customer."
        else:
            effective_price = None
            explanation = "Unknown markup mode."

        return {
            "provider": estimate.provider_key,
            "base_cost": base,
            "price_to_customer": effective_price,
            "gross_margin_amount": margin_amount,
            "gross_margin_percent": margin_pct,
            "markup_mode": mode,
            "margin_status": "blocked_margin" if is_blocked else "safe",
            "is_margin_blocked": is_blocked,
            "explanation": explanation,
        }
