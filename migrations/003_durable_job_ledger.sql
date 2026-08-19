-- VoxFlow Day 25: Durable job ledger and transactional outbox.
-- Apply after migrations/000_base_schema.sql and tenant extensions.
-- All work is tenant-scoped and the file is safe to re-run.

CREATE TABLE IF NOT EXISTS job_runs (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    job_type VARCHAR(128) NOT NULL,
    payload_json TEXT NOT NULL,
    status VARCHAR(32) NOT NULL,
    priority INTEGER NOT NULL,
    idempotency_key VARCHAR(255) NOT NULL,
    scheduled_at TIMESTAMP WITH TIME ZONE NOT NULL,
    next_run_at TIMESTAMP WITH TIME ZONE NOT NULL,
    attempt INTEGER NOT NULL,
    max_attempts INTEGER NOT NULL,
    lease_owner VARCHAR(128),
    lease_expires_at TIMESTAMP WITH TIME ZONE,
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE,
    last_error_code VARCHAR(128),
    last_error_json TEXT,
    trace_id VARCHAR(128),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT uq_job_runs_tenant_idempotency UNIQUE (tenant_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS job_outbox (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    event_type VARCHAR(128) NOT NULL,
    aggregate_type VARCHAR(128) NOT NULL,
    aggregate_id VARCHAR(64) NOT NULL,
    payload_json TEXT NOT NULL,
    idempotency_key VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_job_outbox_tenant_idempotency UNIQUE (tenant_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS job_attempts (
    id VARCHAR(64) PRIMARY KEY,
    job_id VARCHAR(64) NOT NULL REFERENCES job_runs(id),
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    attempt_no INTEGER NOT NULL,
    worker_id VARCHAR(128) NOT NULL,
    outcome VARCHAR(32) NOT NULL,
    provider_request_id VARCHAR(128),
    error_code VARCHAR(128),
    error_json TEXT,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT uq_job_attempts_job_attempt UNIQUE (job_id, attempt_no)
);

CREATE TABLE IF NOT EXISTS provider_operations (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    provider VARCHAR(64) NOT NULL,
    operation_type VARCHAR(64) NOT NULL,
    idempotency_key VARCHAR(255) NOT NULL,
    provider_id VARCHAR(128),
    request_hash VARCHAR(128),
    status VARCHAR(32) NOT NULL,
    requested_at TIMESTAMP WITH TIME ZONE NOT NULL,
    confirmed_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT uq_provider_operations_idempotency
        UNIQUE (tenant_id, provider, operation_type, idempotency_key)
);

CREATE INDEX IF NOT EXISTS ix_job_runs_claim
    ON job_runs (status, next_run_at, priority, scheduled_at);
CREATE INDEX IF NOT EXISTS ix_job_runs_lease
    ON job_runs (lease_expires_at);
CREATE INDEX IF NOT EXISTS ix_job_runs_tenant_id
    ON job_runs (tenant_id);
CREATE INDEX IF NOT EXISTS ix_job_runs_job_type
    ON job_runs (job_type);
CREATE INDEX IF NOT EXISTS ix_job_runs_trace_id
    ON job_runs (trace_id);
CREATE INDEX IF NOT EXISTS ix_job_outbox_unpublished
    ON job_outbox (published_at, created_at);
CREATE INDEX IF NOT EXISTS ix_job_outbox_tenant_id
    ON job_outbox (tenant_id);
CREATE INDEX IF NOT EXISTS ix_job_outbox_event_type
    ON job_outbox (event_type);
CREATE INDEX IF NOT EXISTS ix_job_outbox_aggregate_id
    ON job_outbox (aggregate_id);
CREATE INDEX IF NOT EXISTS ix_job_attempts_job_id
    ON job_attempts (job_id);
CREATE INDEX IF NOT EXISTS ix_job_attempts_tenant_id
    ON job_attempts (tenant_id);
CREATE INDEX IF NOT EXISTS ix_provider_operations_tenant_id
    ON provider_operations (tenant_id);
CREATE INDEX IF NOT EXISTS ix_provider_operations_provider
    ON provider_operations (provider);
CREATE INDEX IF NOT EXISTS ix_provider_operations_operation_type
    ON provider_operations (operation_type);
CREATE INDEX IF NOT EXISTS ix_provider_operations_provider_id
    ON provider_operations (provider_id);
CREATE INDEX IF NOT EXISTS ix_provider_operations_status
    ON provider_operations (status);

ALTER TABLE job_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_outbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE provider_operations ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_policy ON job_runs;
CREATE POLICY tenant_isolation_policy ON job_runs
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON job_outbox;
CREATE POLICY tenant_isolation_policy ON job_outbox
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON job_attempts;
CREATE POLICY tenant_isolation_policy ON job_attempts
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON provider_operations;
CREATE POLICY tenant_isolation_policy ON provider_operations
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
