-- Migration 026: Phase 2 Revenue Infrastructure (Subscriptions & Invoices)
-- Establishes dedicated subscriptions and invoices tables with RLS and dunning tracking.

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS failed_payment_count INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS subscriptions (
    id VARCHAR(128) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    stripe_customer_id VARCHAR(128),
    status VARCHAR(32) NOT NULL DEFAULT 'trialing',
    plan_tier VARCHAR(32) NOT NULL DEFAULT 'starter',
    current_period_start TIMESTAMP WITH TIME ZONE,
    current_period_end TIMESTAMP WITH TIME ZONE,
    cancel_at_period_end INTEGER NOT NULL DEFAULT 0,
    canceled_at TIMESTAMP WITH TIME ZONE,
    failed_payment_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_subscriptions_tenant_id ON subscriptions (tenant_id);
CREATE INDEX IF NOT EXISTS ix_subscriptions_stripe_customer_id ON subscriptions (stripe_customer_id);
CREATE INDEX IF NOT EXISTS ix_subscriptions_status ON subscriptions (status);

ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON subscriptions;
CREATE POLICY tenant_isolation_policy ON subscriptions
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));

CREATE TABLE IF NOT EXISTS invoices (
    id VARCHAR(128) PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    subscription_id VARCHAR(128),
    amount_due_pence INTEGER NOT NULL DEFAULT 0,
    amount_paid_pence INTEGER NOT NULL DEFAULT 0,
    currency VARCHAR(8) NOT NULL DEFAULT 'gbp',
    status VARCHAR(32) NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 1,
    next_payment_attempt TIMESTAMP WITH TIME ZONE,
    invoice_pdf_url TEXT,
    hosted_invoice_url TEXT,
    paid_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_invoices_tenant_id ON invoices (tenant_id);
CREATE INDEX IF NOT EXISTS ix_invoices_subscription_id ON invoices (subscription_id);
CREATE INDEX IF NOT EXISTS ix_invoices_status ON invoices (status);
CREATE INDEX IF NOT EXISTS ix_invoices_tenant_created ON invoices (tenant_id, created_at);

ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON invoices;
CREATE POLICY tenant_isolation_policy ON invoices
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
