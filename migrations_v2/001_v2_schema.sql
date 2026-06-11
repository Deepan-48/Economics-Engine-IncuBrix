-- Economics Engine v2 — Reference SQL Schema
-- SQLAlchemy creates these automatically on startup via init_db()
-- This file is for reference only (PostgreSQL production use)

-- v2 pricing profiles
CREATE TABLE IF NOT EXISTS v2_pricing_profiles (
    id VARCHAR(36) PRIMARY KEY,
    provider_key VARCHAR(64) NOT NULL,
    model_key VARCHAR(128) NOT NULL DEFAULT 'default',
    profile_version INTEGER NOT NULL DEFAULT 1,
    environment VARCHAR(32) NOT NULL DEFAULT 'production',
    source_type VARCHAR(32) NOT NULL DEFAULT 'manual',
    approval_status VARCHAR(32) NOT NULL DEFAULT 'active',
    effective_from TIMESTAMP,
    effective_to TIMESTAMP,
    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
    profile_data TEXT NOT NULL,
    rate_cards TEXT,
    modifiers TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- v2 estimates
CREATE TABLE IF NOT EXISTS v2_estimates (
    id VARCHAR(36) PRIMARY KEY,
    request_id VARCHAR(36) NOT NULL,
    correlation_id VARCHAR(36),
    idempotency_key VARCHAR(256) UNIQUE,
    job_fingerprint VARCHAR(64),
    workspace_id VARCHAR(36),
    project_id VARCHAR(36),
    campaign_id VARCHAR(36),
    provider_key VARCHAR(64) NOT NULL,
    model_key VARCHAR(128) NOT NULL DEFAULT 'default',
    execution_mode VARCHAR(32) NOT NULL DEFAULT 'sync',
    estimated_low_cost DECIMAL(12,4) NOT NULL,
    estimated_base_cost DECIMAL(12,4) NOT NULL,
    estimated_high_cost DECIMAL(12,4) NOT NULL,
    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
    confidence_class VARCHAR(16) NOT NULL,
    cost_class VARCHAR(16) NOT NULL,
    budget_status VARCHAR(32) NOT NULL DEFAULT 'safe',
    margin_status VARCHAR(32) NOT NULL DEFAULT 'safe',
    final_score DECIMAL(8,4),
    is_recommended BOOLEAN NOT NULL DEFAULT FALSE,
    explanation TEXT,
    cost_components TEXT,
    cost_drivers TEXT,
    pricing_profile_version VARCHAR(64),
    policy_version VARCHAR(16) NOT NULL DEFAULT 'v2.0',
    formula_version VARCHAR(16) NOT NULL DEFAULT 'v2.0',
    is_async_batch BOOLEAN NOT NULL DEFAULT FALSE,
    async_savings_percent DECIMAL(6,2),
    retry_exposure DECIMAL(12,4),
    per_output_cost DECIMAL(12,4),
    simulation_mode BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- budget reservations
CREATE TABLE IF NOT EXISTS v2_budget_reservations (
    id VARCHAR(36) PRIMARY KEY,
    estimate_id VARCHAR(36) NOT NULL,
    workspace_id VARCHAR(36),
    campaign_id VARCHAR(36),
    scope_type VARCHAR(32) NOT NULL DEFAULT 'job',
    scope_id VARCHAR(36),
    reserved_amount DECIMAL(12,4) NOT NULL,
    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
    status VARCHAR(32) NOT NULL DEFAULT 'reserved',
    expires_at TIMESTAMP,
    settled_amount DECIMAL(12,4),
    released_amount DECIMAL(12,4),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ledger entries (append-only)
CREATE TABLE IF NOT EXISTS v2_ledger_entries (
    id VARCHAR(36) PRIMARY KEY,
    workspace_id VARCHAR(36),
    project_id VARCHAR(36),
    campaign_id VARCHAR(36),
    job_id VARCHAR(36),
    provider_key VARCHAR(64),
    use_case VARCHAR(128),
    entry_type VARCHAR(32) NOT NULL,
    amount DECIMAL(12,4) NOT NULL,
    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
    source_ref VARCHAR(128),
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- scenarios
CREATE TABLE IF NOT EXISTS v2_scenarios (
    id VARCHAR(36) PRIMARY KEY,
    scenario_name VARCHAR(256) NOT NULL,
    input_config TEXT NOT NULL,
    result_summary TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'completed',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- config versions
CREATE TABLE IF NOT EXISTS v2_config_versions (
    id VARCHAR(36) PRIMARY KEY,
    provider_key VARCHAR(64) NOT NULL,
    version_number INTEGER NOT NULL,
    approval_status VARCHAR(32) NOT NULL DEFAULT 'staged',
    draft_profile TEXT NOT NULL,
    validation_result TEXT,
    impact_preview TEXT,
    approved_by VARCHAR(128),
    created_by VARCHAR(128),
    activated_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- actual costs
CREATE TABLE IF NOT EXISTS v2_actual_costs (
    id VARCHAR(36) PRIMARY KEY,
    provider_key VARCHAR(64) NOT NULL,
    provider_job_id VARCHAR(256),
    provider_request_id VARCHAR(256),
    estimate_id VARCHAR(36),
    job_id VARCHAR(36),
    workspace_id VARCHAR(36),
    actual_amount DECIMAL(12,4) NOT NULL,
    currency VARCHAR(8) NOT NULL DEFAULT 'USD',
    billing_unit VARCHAR(64),
    unit_quantity DECIMAL(12,4),
    import_source VARCHAR(32) NOT NULL DEFAULT 'manual',
    map_status VARCHAR(32) NOT NULL DEFAULT 'unmapped',
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- cost variances
CREATE TABLE IF NOT EXISTS v2_cost_variances (
    id VARCHAR(36) PRIMARY KEY,
    estimate_id VARCHAR(36) NOT NULL,
    actual_cost_id VARCHAR(36) NOT NULL,
    provider_key VARCHAR(64) NOT NULL,
    workspace_id VARCHAR(36),
    estimated_amount DECIMAL(12,4) NOT NULL,
    actual_amount DECIMAL(12,4) NOT NULL,
    variance_amount DECIMAL(12,4) NOT NULL,
    variance_percent DECIMAL(8,2) NOT NULL,
    variance_reason VARCHAR(256),
    severity VARCHAR(16) NOT NULL DEFAULT 'low',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- economics alerts
CREATE TABLE IF NOT EXISTS v2_economics_alerts (
    id VARCHAR(36) PRIMARY KEY,
    alert_type VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL DEFAULT 'medium',
    workspace_id VARCHAR(36),
    provider_key VARCHAR(64),
    title VARCHAR(256) NOT NULL,
    description TEXT,
    evidence TEXT,
    is_resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- events
CREATE TABLE IF NOT EXISTS v2_events (
    id VARCHAR(36) PRIMARY KEY,
    event_type VARCHAR(128) NOT NULL,
    schema_version VARCHAR(16) NOT NULL DEFAULT 'v2.0',
    correlation_id VARCHAR(36),
    request_id VARCHAR(36),
    workspace_id VARCHAR(36),
    properties TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
