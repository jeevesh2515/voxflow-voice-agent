-- Day 32: signed provider callback lifecycle and idempotent reconciliation.
-- Apply after 003_durable_job_ledger.sql, 004_outbox_relay_state.sql, and
-- 005_campaign_policy_controls.sql.

CREATE TABLE IF NOT EXISTS provider_events (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    provider_operation_id VARCHAR(64) NOT NULL REFERENCES provider_operations(id),
    provider VARCHAR(64) NOT NULL,
    provider_event_id VARCHAR(128) NOT NULL,
    provider_call_id VARCHAR(128) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    payload_hash VARCHAR(128) NOT NULL,
    normalized_payload_json TEXT NOT NULL DEFAULT '{}',
    apply_status VARCHAR(32) NOT NULL DEFAULT 'applied',
    anomaly_code VARCHAR(128),
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_provider_events_provider_event UNIQUE (provider, provider_event_id)
);

CREATE INDEX IF NOT EXISTS ix_provider_events_operation_occurred
    ON provider_events (provider_operation_id, occurred_at);
CREATE INDEX IF NOT EXISTS ix_provider_events_tenant_created
    ON provider_events (tenant_id, created_at);

CREATE TABLE IF NOT EXISTS provider_callback_quarantines (
    id VARCHAR(64) PRIMARY KEY,
    provider VARCHAR(64) NOT NULL,
    provider_event_id VARCHAR(128) NOT NULL,
    provider_call_id VARCHAR(128) NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    payload_hash VARCHAR(128) NOT NULL,
    reason_code VARCHAR(128) NOT NULL DEFAULT 'unknown_provider_operation',
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_provider_callback_quarantine_event UNIQUE (provider, provider_event_id)
);

CREATE INDEX IF NOT EXISTS ix_provider_callback_quarantine_created
    ON provider_callback_quarantines (created_at);
