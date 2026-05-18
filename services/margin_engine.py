"""
services/margin_engine.py

Handles margin and markup simulation.
Supports three modes from PRD Section 9.4:
  - pass_through     : customer pays exactly what provider charges
  - markup           : customer pays cost + fixed markup percent
  - protected_margin : block route if margin falls below target

ECO-FR-032, ECO-FR-033
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from schemas.economics_schema import RouteEstimate, MarkupMode


@dataclass
class MarginResult:
    provider: str
    base_cost: float
    price_to_customer: Optional[float]
    gross_margin_amount: Optional[float]
    gross_margin_percent: Optional[float]
    markup_mode: str
    is_margin_blocked: bool
    explanation: str


class MarginEngine:

    def calculate(
        self,
        route: RouteEstimate,
        markup_mode: Optional[MarkupMode],
        price_to_customer: Optional[float],
        target_margin_percent: Optional[float],
    ) -> MarginResult:

        base = route.estimated_base_cost
        mode = markup_mode.value if markup_mode else "pass_through"
        is_blocked = False
        margin_amount = None
        margin_pct = None
        effective_price = price_to_customer

        if mode == "pass_through":
            effective_price = base
            explanation = f"Pass-through mode: customer pays provider cost ${base:.2f}."

        elif mode == "markup":
            if price_to_customer and price_to_customer > base:
                margin_amount = round(price_to_customer - base, 4)
                margin_pct = round((margin_amount / price_to_customer) * 100, 2)
                explanation = (
                    f"Markup mode: cost ${base:.2f}, "
                    f"price ${price_to_customer:.2f}, "
                    f"margin {margin_pct:.1f}%."
                )
            else:
                explanation = f"Markup mode: price_to_customer not provided or below cost."

        elif mode == "protected_margin":
            if price_to_customer and price_to_customer > 0:
                margin_amount = round(price_to_customer - base, 4)
                margin_pct = round((margin_amount / price_to_customer) * 100, 2)

                if target_margin_percent and margin_pct < target_margin_percent:
                    is_blocked = True
                    explanation = (
                        f"Protected margin: margin {margin_pct:.1f}% is below "
                        f"target {target_margin_percent:.1f}%. Route blocked."
                    )
                else:
                    explanation = (
                        f"Protected margin: margin {margin_pct:.1f}% meets "
                        f"target {target_margin_percent or 0:.1f}%. Route allowed."
                    )
            else:
                explanation = "Protected margin: price_to_customer required for this mode."
        else:
            explanation = "Unknown markup mode."

        return MarginResult(
            provider=route.provider,
            base_cost=base,
            price_to_customer=effective_price,
            gross_margin_amount=margin_amount,
            gross_margin_percent=margin_pct,
            markup_mode=mode,
            is_margin_blocked=is_blocked,
            explanation=explanation,
        )
