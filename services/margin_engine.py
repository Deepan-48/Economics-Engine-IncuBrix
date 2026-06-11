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
    def calculate(self, route, markup_mode, price_to_customer, target_margin_percent):
        base = route.estimated_base_cost
        mode = markup_mode.value if markup_mode else "pass_through"
        is_blocked, margin_amount, margin_pct = False, None, None
        if mode == "pass_through":
            return MarginResult(route.provider, base, base, 0.0, 0.0, mode, False, f"Pass-through: ${base:.2f}.")
        elif mode == "markup":
            if price_to_customer and price_to_customer > base:
                margin_amount = round(price_to_customer - base, 4)
                margin_pct = round((margin_amount / price_to_customer) * 100, 2)
                return MarginResult(route.provider, base, price_to_customer, margin_amount, margin_pct, mode, False, f"Markup: cost ${base:.2f}, price ${price_to_customer:.2f}, margin {margin_pct:.1f}%.")
            return MarginResult(route.provider, base, price_to_customer, None, None, mode, False, "Markup: price not set or below cost.")
        elif mode == "protected_margin":
            if price_to_customer and price_to_customer > 0:
                margin_amount = round(price_to_customer - base, 4)
                margin_pct = round((margin_amount / price_to_customer) * 100, 2)
                if target_margin_percent and margin_pct < target_margin_percent:
                    return MarginResult(route.provider, base, price_to_customer, margin_amount, margin_pct, mode, True, f"Protected margin: {margin_pct:.1f}% below target {target_margin_percent:.1f}%. Blocked.")
                return MarginResult(route.provider, base, price_to_customer, margin_amount, margin_pct, mode, False, f"Protected margin: {margin_pct:.1f}% meets target.")
        return MarginResult(route.provider, base, None, None, None, mode, False, "Unknown markup mode.")
