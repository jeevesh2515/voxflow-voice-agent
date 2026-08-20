-- Day 34: typed durable side-effect intent ledger
-- Apply after 007_dial_sandbox_callback_adapter.sql.
-- The JobRun and JobOutbox rows are created transactionally by application code;
-- this table adds redacted intent evidence for Sheets, email, CRM, notifications,
-- and recording retrieval without duplicating raw external payloads.

CREATE TABLE IF NOT EXISTS side_effect_intents (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    job_id VARCHAR(64) NOT NULL REFERENCES job_runs(id),
    effect_type VARCHAR(128) NOT NULL,
    aggregate_type VARCHAR(128) NOT NULL,
    aggregate_id VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(255) NOT NULL,
    payload_hash VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    result_code VARCHAR(128),
    result_json TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_side_effect_intent_idempotency
    ON side_effect_intents (tenant_id, idempotency_key);
CREATE UNIQUE INDEX IF NOT EXISTS uq_side_effect_intent_job
    ON side_effect_intents (job_id);
CREATE INDEX IF NOT EXISTS ix_side_effect_intent_tenant_type_status
    ON side_effect_intents (tenant_id, effect_type, status, created_at);
