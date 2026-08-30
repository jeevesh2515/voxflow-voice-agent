-- Migration 022: Stripe Billing Lifecycle & Invoice Audit Log
-- Adds subscription state to tenants and an immutable per-tenant invoice ledger.
--
-- Only Stripe-issued identifiers, amounts, and hosted URLs are stored. Card
-- numbers, PAN fragments, and payment-method secrets never enter this schema —
-- Stripe Checkout and the Customer Portal own that data end to end.

ALTER TABLE tenants ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(128);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(128);
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(32) NOT NULL DEFAULT 'trialing';
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS current_period_end TIMESTAMP WITH TIME ZONE;
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS cancel_at_period_end INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS ix_tenants_stripe_customer_id ON tenants (stripe_customer_id);

CREATE TABLE IF NOT EXISTS tenant_billing_invoices (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL REFERENCES tenants(id),
    stripe_invoice_id VARCHAR(128) NOT NULL,
    amount_paid_cents INTEGER NOT NULL DEFAULT 0,
    currency VARCHAR(8) NOT NULL DEFAULT 'gbp',
    status VARCHAR(32) NOT NULL,
    invoice_pdf_url TEXT,
    hosted_invoice_url TEXT,
    paid_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Stripe retries a webhook until it receives a 2xx, so the same
-- invoice.payment_succeeded event can arrive several times. This constraint is
-- what makes replaying one idempotent instead of duplicating a billing row.
CREATE UNIQUE INDEX IF NOT EXISTS uq_tenant_billing_invoice_stripe_id
    ON tenant_billing_invoices (tenant_id, stripe_invoice_id);
CREATE INDEX IF NOT EXISTS ix_tenant_billing_invoices_tenant_created
    ON tenant_billing_invoices (tenant_id, created_at);

ALTER TABLE tenant_billing_invoices ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation_policy ON tenant_billing_invoices;
CREATE POLICY tenant_isolation_policy ON tenant_billing_invoices
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
