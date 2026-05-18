"""
services/cost_normalizer.py

Converts each provider's native pricing units into normalized USD estimates.
One function per provider type, called by the EstimationEngine.

Providers:
  - openai    : per_second  × rate, with optional 50% batch discount
  - runway    : credits     × $0.01/credit
  - fal       : flat        model-level price × duration multiplier
  - replicate : runtime     × hardware rate
  - piapi     : credits     × $0.008, with account-mode multiplier

Returns a dict:
  {
    "base_cost": float,   # central estimate
    "low_cost":  float,   # optimistic bound
    "high_cost": float,   # pessimistic bound
    "is_async_batch": bool,
    "async_savings_percent": float | None,
  }

Satisfies: ECO-FR-020, ECO-FR-021, ECO-FR-023, ECO-FR-024
"""

from __future__ import annotations
from typing import Optional
from schemas.economics_schema import DurationClass, QualityBar, LatencyMode


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _apply_uncertainty(base: float, profile: dict) -> tuple[float, float]:
    """Return (low, high) using the provider's uncertainty multipliers."""
    um = profile.get("uncertainty_multiplier", {"low": 0.9, "high": 1.2})
    return round(base * um["low"], 4), round(base * um["high"], 4)


def _duration_key(duration_class: DurationClass) -> str:
    return duration_class.value  # "short" | "medium" | "long"


# ---------------------------------------------------------------------------
# OpenAI normalizer
# ---------------------------------------------------------------------------

def normalize_openai(
    profile: dict,
    duration_class: DurationClass,
    quality_bar: QualityBar,
    latency_mode: LatencyMode,
    batch_size: int,
) -> dict:
    """
    Estimate = seconds × rate_per_second × quality_multiplier × batch_size
    If latency_mode == async_ok AND provider supports batch discount → apply 50% off.
    """
    dk = _duration_key(duration_class)
    seconds = profile["base_assumptions"][f"{dk}_seconds"]
    rate = profile.get("rate_per_second", 0.030)
    quality_mult = profile.get("quality_multiplier", {}).get(quality_bar.value, 1.0)

    base_per_unit = seconds * rate * quality_mult
    base_cost = round(base_per_unit * batch_size, 4)

    is_async = (
        latency_mode == LatencyMode.async_ok
        and profile.get("supports_batch_discount", False)
    )
    async_savings_pct = None

    if is_async:
        discount = profile.get("batch_discount_percent", 0) / 100.0
        async_cost = round(base_cost * (1 - discount), 4)
        async_savings_pct = round(discount * 100, 1)
        low, high = _apply_uncertainty(async_cost, profile)
        return {
            "base_cost": async_cost,
            "low_cost": low,
            "high_cost": high,
            "is_async_batch": True,
            "async_savings_percent": async_savings_pct,
        }

    low, high = _apply_uncertainty(base_cost, profile)
    return {
        "base_cost": base_cost,
        "low_cost": low,
        "high_cost": high,
        "is_async_batch": False,
        "async_savings_percent": None,
    }


# ---------------------------------------------------------------------------
# Runway normalizer
# ---------------------------------------------------------------------------

def normalize_runway(
    profile: dict,
    duration_class: DurationClass,
    quality_bar: QualityBar,
    batch_size: int,
) -> dict:
    """
    Estimate = credits × credit_price × quality_multiplier × batch_size
    """
    dk = _duration_key(duration_class)
    credits_per_unit = profile["base_assumptions"][f"{dk}_credits"]
    credit_price = profile.get("credit_price_usd", 0.01)
    quality_mult = profile.get("quality_multiplier", {}).get(quality_bar.value, 1.0)

    base_cost = round(credits_per_unit * credit_price * quality_mult * batch_size, 4)
    low, high = _apply_uncertainty(base_cost, profile)

    return {
        "base_cost": base_cost,
        "low_cost": low,
        "high_cost": high,
        "is_async_batch": False,
        "async_savings_percent": None,
    }


# ---------------------------------------------------------------------------
# fal normalizer
# ---------------------------------------------------------------------------

def normalize_fal(
    profile: dict,
    duration_class: DurationClass,
    quality_bar: QualityBar,
    batch_size: int,
) -> dict:
    """
    Estimate = model_price[quality] × duration_multiplier × batch_size
    """
    dk = _duration_key(duration_class)
    model_price = profile["model_pricing"].get(quality_bar.value, 0.080)
    dur_mult = profile["base_assumptions"].get(f"{dk}_multiplier", 1.0)

    base_cost = round(model_price * dur_mult * batch_size, 4)
    low, high = _apply_uncertainty(base_cost, profile)

    return {
        "base_cost": base_cost,
        "low_cost": low,
        "high_cost": high,
        "is_async_batch": False,
        "async_savings_percent": None,
    }


# ---------------------------------------------------------------------------
# Replicate normalizer
# ---------------------------------------------------------------------------

def normalize_replicate(
    profile: dict,
    duration_class: DurationClass,
    batch_size: int,
) -> dict:
    """
    Estimate = runtime_seconds × hardware_rate × batch_size
    Hardware is selected by duration class.
    """
    dk = _duration_key(duration_class)
    hardware_key = profile["duration_class_hardware"].get(dk, "standard")
    rate = profile["hardware_profiles"][hardware_key]["rate_per_second"]
    runtime_seconds = profile["base_assumptions"][f"{dk}_seconds"]

    base_cost = round(runtime_seconds * rate * batch_size, 4)
    low, high = _apply_uncertainty(base_cost, profile)

    return {
        "base_cost": base_cost,
        "low_cost": low,
        "high_cost": high,
        "is_async_batch": False,
        "async_savings_percent": None,
    }


# ---------------------------------------------------------------------------
# PiAPI normalizer
# ---------------------------------------------------------------------------

def normalize_piapi(
    profile: dict,
    duration_class: DurationClass,
    quality_bar: QualityBar,
    batch_size: int,
) -> dict:
    """
    Estimate = credits × credit_price × quality_mult × account_mode_mult × batch_size
    """
    dk = _duration_key(duration_class)
    credits_per_unit = profile["base_assumptions"][f"{dk}_credits"]
    credit_price = profile.get("credit_price_usd", 0.008)
    quality_mult = profile.get("quality_multiplier", {}).get(quality_bar.value, 1.0)
    account_mode = profile.get("account_mode", "pay_as_you_go")
    mode_mult = profile.get("account_mode_multiplier", {}).get(account_mode, 1.0)

    base_cost = round(credits_per_unit * credit_price * quality_mult * mode_mult * batch_size, 4)
    low, high = _apply_uncertainty(base_cost, profile)

    return {
        "base_cost": base_cost,
        "low_cost": low,
        "high_cost": high,
        "is_async_batch": False,
        "async_savings_percent": None,
    }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def normalize_cost(
    profile: dict,
    duration_class: DurationClass,
    quality_bar: QualityBar,
    latency_mode: LatencyMode,
    batch_size: int,
) -> dict:
    """
    Dispatcher: routes to the correct normalizer based on pricing_unit.
    Returns standardized cost dict.
    """
    pricing_unit = profile.get("pricing_unit", "")
    provider_key = profile.get("provider_key", "unknown")

    if pricing_unit == "per_second":
        return normalize_openai(profile, duration_class, quality_bar, latency_mode, batch_size)
    elif pricing_unit == "credits":
        return normalize_runway(profile, duration_class, quality_bar, batch_size)
    elif pricing_unit == "flat":
        return normalize_fal(profile, duration_class, quality_bar, batch_size)
    elif pricing_unit == "runtime":
        return normalize_replicate(profile, duration_class, batch_size)
    elif pricing_unit == "credits_account_mode":
        return normalize_piapi(profile, duration_class, quality_bar, batch_size)
    else:
        raise ValueError(
            f"Unknown pricing_unit '{pricing_unit}' for provider '{provider_key}'"
        )
