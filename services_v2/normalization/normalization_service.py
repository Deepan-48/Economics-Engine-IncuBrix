"""
services_v2/normalization/normalization_service.py

ECO2-NORM-001 to ECO2-NORM-003
"""

from __future__ import annotations
from schemas_v2.economics_v2_schema import DurationClass, QualityBar, LatencyMode, CostComponent

FORMULA_VERSION = "v2.0"

DURATION_SECONDS = {"short": 8, "medium": 20, "long": 45}
QUALITY_MULTIPLIERS = {"acceptable": 0.80, "high": 1.00, "premium": 1.35}

MODIFIER_ORDER = [
    "quality_multiplier",
    "account_mode_multiplier",
    "batch_discount",
    "tax",
    "fx_buffer",
    "uncertainty_buffer",
]


def _apply_modifiers(base: float, modifiers: list[dict], context: dict) -> tuple[float, list[str]]:
    result = base
    applied = []
    modifier_map = {m["modifier_type"]: m for m in modifiers}

    for mod_type in MODIFIER_ORDER:
        if mod_type not in modifier_map:
            continue
        mod = modifier_map[mod_type]
        condition = mod.get("condition", "")

        if condition and "=" in condition:
            key, val = condition.split("=", 1)
            if str(context.get(key.strip(), "")).lower() != val.strip().lower():
                continue

        val = mod["value"]
        vtype = mod["value_type"]

        if vtype == "percent" and "discount" in mod_type:
            result = result * (1 - val / 100)
        elif vtype == "percent":
            result = result * (1 + val / 100)
        elif vtype == "multiplier":
            result = result * val

        applied.append(f"{mod_type}({val}{vtype})")

    return round(result, 6), applied


def normalize_provider_cost(
    profile: dict,
    duration_class: DurationClass,
    quality_bar: QualityBar,
    latency_mode: LatencyMode,
    batch_size: int,
    variant_count: int = 1,
) -> dict:

    provider_key     = profile.get("provider_key", "unknown")
    rate_cards       = profile.get("rate_cards", [])
    modifiers        = profile.get("modifiers", [])
    base_assumptions = profile.get("base_assumptions", {})
    unc_low  = profile.get("default_uncertainty_multiplier_low", 0.9)
    unc_high = profile.get("default_uncertainty_multiplier_high", 1.2)

    dk = duration_class.value
    seconds = base_assumptions.get(f"{dk}_seconds", DURATION_SECONDS.get(dk, 10))
    quality_mult = QUALITY_MULTIPLIERS.get(quality_bar.value, 1.0)
    total_units = batch_size * variant_count

    is_async = latency_mode.value == "async_ok" and profile.get("supports_batch_discount", False)
    context = {
        "execution_mode": "batch" if is_async else "sync",
        "currency_conversion": "false",
    }

    # pick rate card matching quality
    primary_rc = None
    for rc in rate_cards:
        if rc.get("quality_class") == quality_bar.value:
            primary_rc = rc
            break
    if not primary_rc and rate_cards:
        for rc in rate_cards:
            if rc.get("quality_class") in (None, "standard", "high"):
                primary_rc = rc
                break
    if not primary_rc and rate_cards:
        primary_rc = rate_cards[0]

    if not primary_rc:
        unit_type = "per_second"
        unit_rate = base_assumptions.get("rate_per_second", 0.03)
        unit_qty  = seconds
    else:
        unit_type = primary_rc.get("unit_type", "per_second")
        unit_rate = primary_rc.get("unit_rate", 0.03)

        if unit_type == "per_second":
            unit_qty = seconds
        elif unit_type == "credits":
            unit_qty = base_assumptions.get(f"{dk}_credits", 50)
        elif unit_type in ("per_output", "flat_fee"):
            unit_qty = 1.0
            dur_mult = base_assumptions.get(f"{dk}_multiplier", 1.0)
            unit_rate = unit_rate * dur_mult
        elif unit_type == "per_runtime_second":
            hw_map = base_assumptions.get("duration_class_hardware", {})
            hw_key = hw_map.get(dk, "standard")
            hw_profiles = base_assumptions.get("hardware_profiles", {})
            unit_rate = hw_profiles.get(hw_key, {}).get("rate_per_second", unit_rate)
            unit_qty = base_assumptions.get(f"{dk}_seconds", seconds)
        else:
            unit_qty = seconds

    adjusted_rate = unit_rate * quality_mult
    raw_base = adjusted_rate * unit_qty * total_units

    final_base, applied_modifiers = _apply_modifiers(raw_base, modifiers, context)

    base_cost = round(final_base, 4)
    low_cost  = round(final_base * unc_low, 4)
    high_cost = round(final_base * unc_high, 4)

    component = CostComponent(
        unit_type=unit_type,
        unit_quantity=round(unit_qty * total_units, 4),
        unit_rate=adjusted_rate,
        currency=profile.get("currency", "USD"),
        modifier_applied=", ".join(applied_modifiers) if applied_modifiers else None,
        low_cost=low_cost,
        base_cost=base_cost,
        high_cost=high_cost,
        formula_version=FORMULA_VERSION,
        contribution_percent=100.0,
    )

    async_savings_pct = None
    async_base = base_cost
    if is_async:
        disc = profile.get("batch_discount_percent", 0)
        async_base = round(base_cost * (1 - disc / 100), 4)
        async_savings_pct = disc

    trace = {
        "provider":            provider_key,
        "unit_type":           unit_type,
        "unit_quantity":       round(unit_qty * total_units, 4),
        "unit_rate":           adjusted_rate,
        "quality_multiplier":  quality_mult,
        "modifiers_applied":   applied_modifiers,
        "uncertainty_low":     unc_low,
        "uncertainty_high":    unc_high,
        "formula_version":     FORMULA_VERSION,
    }

    return {
        "base_cost":             base_cost,
        "low_cost":              low_cost,
        "high_cost":             high_cost,
        "is_async_batch":        is_async,
        "async_base_cost":       async_base,
        "async_savings_percent": async_savings_pct,
        "cost_components":       [component.model_dump()],
        "normalization_trace":   trace,
    }
