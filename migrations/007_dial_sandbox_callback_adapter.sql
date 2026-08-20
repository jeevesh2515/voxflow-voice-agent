-- Day 33: Dial sandbox callback adapter certification, rollout receipt, and observability.
-- Apply after 006_provider_callback_lifecycle.sql.

CREATE TABLE IF NOT EXISTS provider_callback_adapter_audits (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) REFERENCES tenants(id),
    provider VARCHAR(64) NOT NULL,
    provider_event_id VARCHAR(128) NOT NULL,
    provider_event_type VARCHAR(128),
    payload_hash VARCHAR(128) NOT NULL,
    verification_status VARCHAR(32) NOT NULL,
    normalization_status VARCHAR(32) NOT NULL,
    application_status VARCHAR(32) NOT NULL,
    reason_code VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_provider_callback_adapter_audit_event_payload
        UNIQUE (provider, provider_event_id, payload_hash)
);

CREATE INDEX IF NOT EXISTS ix_provider_callback_adapter_audit_tenant_created
    ON provider_callback_adapter_audits (tenant_id, created_at);
CREATE INDEX IF NOT EXISTS ix_provider_callback_adapter_audit_provider_created
    ON provider_callback_adapter_audits (provider, created_at);
