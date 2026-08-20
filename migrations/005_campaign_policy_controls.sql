-- Day 30: tenant policy controls, recipient consent/opt-out, and auditable cancellation.
-- Apply after 003_durable_job_ledger.sql and 004_outbox_relay_state.sql.

CREATE TABLE IF NOT EXISTS tenant_campaign_policies (
    tenant_id VARCHAR(64) PRIMARY KEY REFERENCES tenants(id),
    timezone_name VARCHAR(64) NOT NULL DEFAULT 'Asia/Kolkata',
    calling_window_start VARCHAR(5) NOT NULL DEFAULT '09:00',
    calling_window_end VARCHAR(5) NOT NULL DEFAULT '20:00',
    daily_call_limit INTEGER NOT NULL DEFAULT 100,
    max_in_flight INTEGER NOT NULL DEFAULT 1,
    enabled INTEGER NOT NULL DEFAULT 1,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_campaign_policy_daily_limit_positive CHECK (daily_call_limit > 0),
    CONSTRAINT ck_campaign_policy_max_in_flight_positive CHECK (max_in_flight > 0),
    CONSTRAINT ck_campaign_policy_window_differs CHECK (calling_window_start <> calling_window_end)
);

CREATE TABLE IF NOT EXISTS recipient_campaign_preferences (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    recipient_phone VARCHAR(32) NOT NULL,
    consent_status VARCHAR(32) NOT NULL DEFAULT 'granted',
    consent_purpose VARCHAR(64) NOT NULL DEFAULT 'outbound_campaign',
    opted_out INTEGER NOT NULL DEFAULT 0,
    source VARCHAR(128) NOT NULL DEFAULT 'tenant_default',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_recipient_campaign_preference UNIQUE (tenant_id, recipient_phone),
    CONSTRAINT ck_recipient_consent_status CHECK (consent_status IN ('granted', 'withdrawn', 'unknown'))
);
CREATE INDEX IF NOT EXISTS ix_recipient_campaign_preferences_tenant_phone
    ON recipient_campaign_preferences (tenant_id, recipient_phone);

CREATE TABLE IF NOT EXISTS tenant_daily_dispatch_usage (
    id VARCHAR(96) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    local_date VARCHAR(10) NOT NULL,
    reserved_calls INTEGER NOT NULL DEFAULT 0,
    active_dispatches INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tenant_dispatch_usage_day UNIQUE (tenant_id, local_date),
    CONSTRAINT ck_dispatch_usage_reserved_nonnegative CHECK (reserved_calls >= 0),
    CONSTRAINT ck_dispatch_usage_active_nonnegative CHECK (active_dispatches >= 0)
);
CREATE INDEX IF NOT EXISTS ix_tenant_daily_dispatch_usage_tenant_date
    ON tenant_daily_dispatch_usage (tenant_id, local_date);

CREATE TABLE IF NOT EXISTS campaign_dispatch_reservations (
    id VARCHAR(64) PRIMARY KEY,
    job_id VARCHAR(64) NOT NULL REFERENCES job_runs(id),
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    local_date VARCHAR(10) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    settled_at TIMESTAMPTZ,
    CONSTRAINT uq_campaign_dispatch_reservation_job UNIQUE (job_id),
    CONSTRAINT ck_campaign_dispatch_reservation_status CHECK (status IN ('active', 'released', 'settled'))
);
CREATE INDEX IF NOT EXISTS ix_campaign_dispatch_reservations_tenant_date
    ON campaign_dispatch_reservations (tenant_id, local_date);

CREATE TABLE IF NOT EXISTS campaign_policy_decisions (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    job_id VARCHAR(64) NOT NULL REFERENCES job_runs(id),
    campaign_id VARCHAR(64) NOT NULL REFERENCES outbound_campaigns(id),
    campaign_queue_id VARCHAR(64) NOT NULL REFERENCES campaign_queue(id),
    decision VARCHAR(32) NOT NULL,
    reason_code VARCHAR(128) NOT NULL,
    evidence_json TEXT NOT NULL DEFAULT '{}',
    next_eligible_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_campaign_policy_decision CHECK (decision IN ('allowed', 'deferred', 'cancelled'))
);
CREATE INDEX IF NOT EXISTS ix_campaign_policy_decisions_target
    ON campaign_policy_decisions (tenant_id, campaign_queue_id, created_at);
