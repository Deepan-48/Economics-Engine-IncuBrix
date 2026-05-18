-- =============================================================================
-- Migration 001 — Initial schema for Economics Engine
-- IncuBrix Video Gen Services — Capability 4
-- Run manually on PostgreSQL, or let SQLAlchemy create_all handle it for SQLite
-- =============================================================================

-- Enable UUID generation (PostgreSQL only)
-- CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ---------------------------------------------------------------------------
-- Table: pricing_profiles
-- Stores versioned provider pricing models (OpenAI, Runway, fal, Replicate, PiAPI)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pricing_profiles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_key        VARCHAR(64)  NOT NULL,
    pricing_profile_json JSONB       NOT NULL,
    version             INTEGER      NOT NULL DEFAULT 1,
    is_active           BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP    NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_provider_version UNIQUE (provider_key, version)
);

CREATE INDEX IF NOT EXISTS idx_pricing_profiles_provider ON pricing_profiles(provider_key);
CREATE INDEX IF NOT EXISTS idx_pricing_profiles_active   ON pricing_profiles(is_active);


-- ---------------------------------------------------------------------------
-- Table: economics_requests
-- One row per incoming estimation request
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS economics_requests (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_payload     JSONB       NOT NULL,
    status              VARCHAR(32) NOT NULL DEFAULT 'completed'
                            CHECK (status IN ('completed', 'blocked', 'failed')),
    recommended_route   VARCHAR(128),
    simulation_mode     BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_econ_requests_status     ON economics_requests(status);
CREATE INDEX IF NOT EXISTS idx_econ_requests_created_at ON economics_requests(created_at DESC);


-- ---------------------------------------------------------------------------
-- Table: economics_decisions
-- One row per provider evaluated for a request (1 request → N decisions)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS economics_decisions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    economics_request_id    UUID        NOT NULL REFERENCES economics_requests(id) ON DELETE CASCADE,
    provider_key            VARCHAR(64) NOT NULL,
    estimated_low_cost      DECIMAL(10,4) NOT NULL,
    estimated_high_cost     DECIMAL(10,4) NOT NULL,
    estimated_base_cost     DECIMAL(10,4) NOT NULL,
    budget_status           VARCHAR(32) NOT NULL DEFAULT 'safe'
                                CHECK (budget_status IN ('safe', 'warning', 'blocked')),
    cost_class              VARCHAR(16) NOT NULL DEFAULT 'medium'
                                CHECK (cost_class IN ('low', 'medium', 'high')),
    confidence_class        VARCHAR(16) NOT NULL DEFAULT 'medium'
                                CHECK (confidence_class IN ('high', 'medium', 'low')),
    final_score             DECIMAL(6,4),
    is_recommended          BOOLEAN     NOT NULL DEFAULT FALSE,
    explanation             TEXT,
    created_at              TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_econ_decisions_request  ON economics_decisions(economics_request_id);
CREATE INDEX IF NOT EXISTS idx_econ_decisions_provider ON economics_decisions(provider_key);


-- ---------------------------------------------------------------------------
-- Table: economics_overrides
-- Records when a user overrides the engine's recommendation
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS economics_overrides (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    economics_request_id    UUID        NOT NULL REFERENCES economics_requests(id) ON DELETE CASCADE,
    original_provider       VARCHAR(64) NOT NULL,
    override_provider       VARCHAR(64) NOT NULL,
    override_reason         TEXT,
    created_at              TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_econ_overrides_request ON economics_overrides(economics_request_id);
