from schemas.economics_schema import DurationClass, QualityBar, LatencyMode

def _apply_uncertainty(base, profile):
    um = profile.get("uncertainty_multiplier", {"low": 0.9, "high": 1.2})
    return round(base * um["low"], 4), round(base * um["high"], 4)

def normalize_openai(profile, duration_class, quality_bar, latency_mode, batch_size):
    dk = duration_class.value
    seconds = profile["base_assumptions"][f"{dk}_seconds"]
    rate = profile.get("rate_per_second", 0.030)
    quality_mult = profile.get("quality_multiplier", {}).get(quality_bar.value, 1.0)
    base_cost = round(seconds * rate * quality_mult * batch_size, 4)
    is_async = latency_mode == LatencyMode.async_ok and profile.get("supports_batch_discount", False)
    if is_async:
        disc = profile.get("batch_discount_percent", 0) / 100.0
        async_cost = round(base_cost * (1 - disc), 4)
        low, high = _apply_uncertainty(async_cost, profile)
        return {"base_cost": async_cost, "low_cost": low, "high_cost": high, "is_async_batch": True, "async_savings_percent": disc * 100}
    low, high = _apply_uncertainty(base_cost, profile)
    return {"base_cost": base_cost, "low_cost": low, "high_cost": high, "is_async_batch": False, "async_savings_percent": None}

def normalize_runway(profile, duration_class, quality_bar, batch_size):
    dk = duration_class.value
    credits = profile["base_assumptions"][f"{dk}_credits"]
    price = profile.get("credit_price_usd", 0.01)
    qm = profile.get("quality_multiplier", {}).get(quality_bar.value, 1.0)
    base = round(credits * price * qm * batch_size, 4)
    low, high = _apply_uncertainty(base, profile)
    return {"base_cost": base, "low_cost": low, "high_cost": high, "is_async_batch": False, "async_savings_percent": None}

def normalize_fal(profile, duration_class, quality_bar, batch_size):
    dk = duration_class.value
    mp = profile["model_pricing"].get(quality_bar.value, 0.080)
    dm = profile["base_assumptions"].get(f"{dk}_multiplier", 1.0)
    base = round(mp * dm * batch_size, 4)
    low, high = _apply_uncertainty(base, profile)
    return {"base_cost": base, "low_cost": low, "high_cost": high, "is_async_batch": False, "async_savings_percent": None}

def normalize_replicate(profile, duration_class, batch_size):
    dk = duration_class.value
    hw = profile["duration_class_hardware"].get(dk, "standard")
    rate = profile["hardware_profiles"][hw]["rate_per_second"]
    secs = profile["base_assumptions"][f"{dk}_seconds"]
    base = round(secs * rate * batch_size, 4)
    low, high = _apply_uncertainty(base, profile)
    return {"base_cost": base, "low_cost": low, "high_cost": high, "is_async_batch": False, "async_savings_percent": None}

def normalize_piapi(profile, duration_class, quality_bar, batch_size):
    dk = duration_class.value
    credits = profile["base_assumptions"][f"{dk}_credits"]
    price = profile.get("credit_price_usd", 0.008)
    qm = profile.get("quality_multiplier", {}).get(quality_bar.value, 1.0)
    mode = profile.get("account_mode", "pay_as_you_go")
    mm = profile.get("account_mode_multiplier", {}).get(mode, 1.0)
    base = round(credits * price * qm * mm * batch_size, 4)
    low, high = _apply_uncertainty(base, profile)
    return {"base_cost": base, "low_cost": low, "high_cost": high, "is_async_batch": False, "async_savings_percent": None}

def normalize_cost(profile, duration_class, quality_bar, latency_mode, batch_size):
    pu = profile.get("pricing_unit", "")
    pk = profile.get("provider_key", "unknown")
    if pu == "per_second": return normalize_openai(profile, duration_class, quality_bar, latency_mode, batch_size)
    elif pu == "credits": return normalize_runway(profile, duration_class, quality_bar, batch_size)
    elif pu == "flat": return normalize_fal(profile, duration_class, quality_bar, batch_size)
    elif pu == "runtime": return normalize_replicate(profile, duration_class, batch_size)
    elif pu == "credits_account_mode": return normalize_piapi(profile, duration_class, quality_bar, batch_size)
    raise ValueError(f"Unknown pricing_unit '{pu}' for provider '{pk}'")
