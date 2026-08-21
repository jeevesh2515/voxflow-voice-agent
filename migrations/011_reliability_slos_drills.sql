-- Day 37: reliability SLO definitions and deterministic drill evidence.
--
-- These tables deliberately hold aggregate controls and receipts only. They
-- never store phone numbers, transcripts, raw queue payloads, callback bodies,
-- signatures, secrets, credentials, or provider request data.  A drill receipt
-- is evidence of an in-memory/database-only fixture; it cannot activate a
-- worker, enqueue work, contact a provider, or execute a recovery plan.

CREATE TABLE IF NOT EXISTS reliability_slos (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    metric_type VARCHAR(64) NOT NULL,
    target_percent DOUBLE PRECISION NOT NULL DEFAULT 100.0,
    window_hours INTEGER NOT NULL DEFAULT 24,
    comparison VARCHAR(16) NOT NULL DEFAULT 'minimum',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_reliability_slo_tenant_metric UNIQUE (tenant_id, metric_type)
);

CREATE INDEX IF NOT EXISTS ix_reliability_slo_tenant_active
    ON reliability_slos (tenant_id, active);

CREATE TABLE IF NOT EXISTS drill_results (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    fixture_type VARCHAR(64) NOT NULL,
    fixture_version VARCHAR(32) NOT NULL DEFAULT 'day37-v1',
    execution_key VARCHAR(128) NOT NULL,
    outcome VARCHAR(32) NOT NULL,
    evidence_json TEXT NOT NULL DEFAULT '{}',
    recovery_summary VARCHAR(512) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_drill_result_execution UNIQUE (tenant_id, fixture_type, execution_key)
);

CREATE INDEX IF NOT EXISTS ix_drill_result_tenant_created
    ON drill_results (tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_drill_result_tenant_fixture
    ON drill_results (tenant_id, fixture_type, created_at DESC);
