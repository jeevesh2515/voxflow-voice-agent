-- Day 28: durable relay leasing and publication diagnostics.
-- Apply after migrations/003_durable_job_ledger.sql. Safe to re-run on Postgres.

ALTER TABLE job_outbox
    ADD COLUMN IF NOT EXISTS relay_owner VARCHAR(128),
    ADD COLUMN IF NOT EXISTS relay_lease_expires_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS publish_attempt INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_error_code VARCHAR(128),
    ADD COLUMN IF NOT EXISTS last_error_json TEXT;

CREATE INDEX IF NOT EXISTS ix_job_outbox_claim
    ON job_outbox (published_at, relay_lease_expires_at, created_at);

CREATE INDEX IF NOT EXISTS ix_job_outbox_relay_owner
    ON job_outbox (relay_owner);
