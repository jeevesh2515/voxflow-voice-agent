-- Tenant roles and membership lifecycle.
--
-- Supabase Auth proves identity. This application-owned ledger controls tenant
-- authorization and does not store a raw invitee email. subject_email_hash is a
-- SHA-256 digest of the normalized recipient address and is used only for a
-- signed-in recipient to accept a pending invitation. No invitation email is
-- sent by this migration or by the membership API.

CREATE TABLE IF NOT EXISTS tenant_members (
    id VARCHAR(64) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    user_id VARCHAR(128),
    subject_email_hash VARCHAR(64) NOT NULL,
    role VARCHAR(16) NOT NULL DEFAULT 'viewer',
    status VARCHAR(16) NOT NULL DEFAULT 'invited',
    invited_by VARCHAR(128) NOT NULL DEFAULT '',
    activated_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    revoked_by VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_tenant_member_user UNIQUE (tenant_id, user_id),
    CONSTRAINT uq_tenant_member_email_hash UNIQUE (tenant_id, subject_email_hash),
    CONSTRAINT ck_tenant_member_role CHECK (role IN ('owner', 'operator', 'viewer')),
    CONSTRAINT ck_tenant_member_status CHECK (status IN ('invited', 'active', 'revoked'))
);

CREATE INDEX IF NOT EXISTS ix_tenant_member_user_status
    ON tenant_members (user_id, status);
CREATE INDEX IF NOT EXISTS ix_tenant_member_tenant_status
    ON tenant_members (tenant_id, status);
