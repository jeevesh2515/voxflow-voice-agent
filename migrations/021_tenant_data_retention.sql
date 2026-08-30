-- Migration 021: Tenant Data Retention & UK GDPR Compliance
-- Adds retention/privacy columns to tenants and immutable purge audit log.

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS call_retention_days INTEGER NOT NULL DEFAULT 90;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS transcript_retention_days INTEGER NOT NULL DEFAULT 30;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS pii_masking_enabled INTEGER NOT NULL DEFAULT 1;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS data_residency_region VARCHAR(32) NOT NULL DEFAULT 'eu-west-2';

CREATE TABLE IF NOT EXISTS retention_purge_logs (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    purged_by_user_id VARCHAR(128),
    execution_type VARCHAR(32) NOT NULL,
    records_scanned INTEGER NOT NULL DEFAULT 0,
    calls_anonymized INTEGER NOT NULL DEFAULT 0,
    transcripts_purged INTEGER NOT NULL DEFAULT 0,
    dry_run INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_retention_purge_logs_tenant_created ON retention_purge_logs (tenant_id, created_at);
CREATE INDEX IF NOT EXISTS ix_retention_purge_logs_execution_type ON retention_purge_logs (execution_type);
