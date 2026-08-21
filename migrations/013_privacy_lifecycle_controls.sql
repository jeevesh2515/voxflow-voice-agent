-- Privacy lifecycle controls: retention settings and redacted request ledger.
-- No raw requester email, phone number, transcript, recording URL, or customer
-- account payload is stored in the request workflow tables.

CREATE TABLE IF NOT EXISTS tenant_privacy_policies (
    tenant_id VARCHAR(64) PRIMARY KEY REFERENCES tenants(id),
    call_transcript_retention_days INTEGER NOT NULL DEFAULT 30,
    communication_retention_days INTEGER NOT NULL DEFAULT 30,
    recording_retention_days INTEGER NOT NULL DEFAULT 0,
    updated_by VARCHAR(128) NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_privacy_transcript_retention_nonnegative CHECK (call_transcript_retention_days >= 0),
    CONSTRAINT ck_privacy_communication_retention_nonnegative CHECK (communication_retention_days >= 0),
    CONSTRAINT ck_privacy_recording_retention_nonnegative CHECK (recording_retention_days >= 0)
);

CREATE TABLE IF NOT EXISTS privacy_requests (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    request_type VARCHAR(32) NOT NULL,
    subject_hash VARCHAR(64) NOT NULL DEFAULT '',
    status VARCHAR(32) NOT NULL DEFAULT 'pending_human_review',
    requested_by VARCHAR(128) NOT NULL DEFAULT '',
    review_note VARCHAR(512) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ,
    reviewed_by VARCHAR(128),
    CONSTRAINT ck_privacy_request_type CHECK (request_type IN ('access_export', 'deletion', 'demo_reset')),
    CONSTRAINT ck_privacy_request_status CHECK (status IN ('pending_human_review', 'human_verification_required', 'approved_for_manual_export', 'blocked', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS ix_privacy_request_tenant_status
    ON privacy_requests (tenant_id, status);
CREATE INDEX IF NOT EXISTS ix_privacy_request_subject_hash
    ON privacy_requests (tenant_id, subject_hash);
