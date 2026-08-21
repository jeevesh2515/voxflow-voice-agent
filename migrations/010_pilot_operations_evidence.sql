-- Day 36: Evidence-led controlled-pilot operations.
--
-- This migration records only redacted aggregate review evidence. It does not
-- enable a worker, register a provider callback, enqueue work, or persist phone
-- numbers, transcripts, webhook bodies, secrets, or raw durable-job payloads.
CREATE TABLE IF NOT EXISTS pilot_operational_evidence (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    pilot_id VARCHAR(96) NOT NULL,
    pilot_version INTEGER NOT NULL DEFAULT 1,
    evidence_kind VARCHAR(32) NOT NULL,
    evidence_key VARCHAR(128) NOT NULL,
    decision VARCHAR(48) NOT NULL,
    reason_code VARCHAR(128) NOT NULL DEFAULT '',
    snapshot_json TEXT NOT NULL DEFAULT '{}',
    recorded_by VARCHAR(128) NOT NULL DEFAULT 'trusted_operator_service',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_pilot_operational_evidence_key UNIQUE (
        tenant_id, pilot_id, pilot_version, evidence_kind, evidence_key
    )
);
CREATE INDEX IF NOT EXISTS ix_pilot_operational_evidence_tenant_created
    ON pilot_operational_evidence(tenant_id, created_at);
CREATE INDEX IF NOT EXISTS ix_pilot_operational_evidence_pilot_kind_created
    ON pilot_operational_evidence(pilot_id, evidence_kind, created_at);
