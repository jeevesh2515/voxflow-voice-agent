-- Day 35: Controlled pilot readiness, redacted cohort admission, and measured security outcomes.
--
-- This migration does not enable a worker, register a callback, enqueue a call,
-- or contain supplier contact data. Production admission remains fail-closed by
-- PILOT_READINESS_ENFORCED=true and an empty PILOT_READINESS_APPROVED_TENANTS.

CREATE TABLE IF NOT EXISTS pilot_configurations (
    tenant_id VARCHAR(64) PRIMARY KEY REFERENCES tenants(id),
    pilot_id VARCHAR(96) NOT NULL UNIQUE,
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    cohort_id VARCHAR(96) NOT NULL,
    cohort_size INTEGER NOT NULL DEFAULT 0,
    timezone_name VARCHAR(64) NOT NULL DEFAULT 'Asia/Kolkata',
    calling_window_start VARCHAR(5) NOT NULL DEFAULT '09:00',
    calling_window_end VARCHAR(5) NOT NULL DEFAULT '20:00',
    daily_call_limit INTEGER NOT NULL DEFAULT 1,
    max_in_flight INTEGER NOT NULL DEFAULT 1,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    primary_escalation_owner VARCHAR(255) NOT NULL DEFAULT '',
    backup_escalation_owner VARCHAR(255) NOT NULL DEFAULT '',
    acknowledgement_timeout_minutes INTEGER NOT NULL DEFAULT 15,
    metric_contract_version VARCHAR(32) NOT NULL DEFAULT 'day35-v1',
    approved_by VARCHAR(255) NOT NULL DEFAULT '',
    approved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_pilot_configurations_status ON pilot_configurations(status);
CREATE INDEX IF NOT EXISTS ix_pilot_configurations_cohort_id ON pilot_configurations(cohort_id);
CREATE INDEX IF NOT EXISTS ix_pilot_configurations_expires_at ON pilot_configurations(expires_at);

CREATE TABLE IF NOT EXISTS pilot_cohort_members (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    cohort_id VARCHAR(96) NOT NULL,
    recipient_hash VARCHAR(64) NOT NULL,
    consent_evidence_ref VARCHAR(128) NOT NULL DEFAULT '',
    status VARCHAR(32) NOT NULL DEFAULT 'approved',
    added_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reviewed_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_pilot_cohort_recipient UNIQUE (tenant_id, cohort_id, recipient_hash)
);

CREATE INDEX IF NOT EXISTS ix_pilot_cohort_member_lookup
    ON pilot_cohort_members(tenant_id, cohort_id, status);

CREATE TABLE IF NOT EXISTS pilot_security_incidents (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    pilot_id VARCHAR(96) NOT NULL,
    category VARCHAR(96) NOT NULL,
    severity VARCHAR(32) NOT NULL DEFAULT 'medium',
    status VARCHAR(32) NOT NULL DEFAULT 'confirmed',
    summary VARCHAR(512) NOT NULL DEFAULT '',
    detected_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS ix_pilot_security_incident_tenant_created
    ON pilot_security_incidents(tenant_id, created_at);
