-- =====================================================================
-- VoxFlow migration 001 — inbound customer-support call flow
-- =====================================================================
--
-- Run this ONCE against your Supabase Postgres database, in the Supabase
-- dashboard: SQL Editor -> New query -> paste -> Run.
--
-- Safe to re-run: every statement uses IF NOT EXISTS / IF EXISTS.
--
-- What it adds:
--   1. PO acknowledgement + dispatch tracking on `orders`
--   2. Structured call-outcome capture on `calls`
--   3. `contact_type` on `suppliers` so one table holds customers + suppliers
--   4. `tenant_phone_numbers` so an inbound number maps to the right tenant
--   5. Indexes for the query patterns the agent actually uses on a live call
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. orders — "have you signed our PO?" and "when did you send it?"
-- ---------------------------------------------------------------------
ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_po_ref VARCHAR(128) DEFAULT '';
ALTER TABLE orders ADD COLUMN IF NOT EXISTS po_signed       INT DEFAULT 0;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS po_signed_at    TIMESTAMPTZ;
ALTER TABLE orders ADD COLUMN IF NOT EXISTS po_signed_by    VARCHAR(255) DEFAULT '';
ALTER TABLE orders ADD COLUMN IF NOT EXISTS dispatched_at   TIMESTAMPTZ;

COMMENT ON COLUMN orders.customer_po_ref IS
    'The customer''s own PO number on their side, e.g. VB/PO/2026/0912. Callers
     quote this, not our internal order id.';
COMMENT ON COLUMN orders.po_signed IS '0 = not signed yet, 1 = signed/acknowledged by us';

-- Callers quote their own reference far more often than ours.
CREATE INDEX IF NOT EXISTS idx_orders_customer_po_ref
    ON orders (tenant_id, customer_po_ref);


-- ---------------------------------------------------------------------
-- 2. calls — why they rang, what we did, were they happy
-- ---------------------------------------------------------------------
ALTER TABLE calls ADD COLUMN IF NOT EXISTS reason             TEXT DEFAULT '';
ALTER TABLE calls ADD COLUMN IF NOT EXISTS solution           TEXT DEFAULT '';
ALTER TABLE calls ADD COLUMN IF NOT EXISTS resolution_status  VARCHAR(16) DEFAULT '';
ALTER TABLE calls ADD COLUMN IF NOT EXISTS satisfaction       VARCHAR(16) DEFAULT '';
ALTER TABLE calls ADD COLUMN IF NOT EXISTS follow_up_required INT DEFAULT 0;
ALTER TABLE calls ADD COLUMN IF NOT EXISTS staff_resolution   TEXT DEFAULT '';
ALTER TABLE calls ADD COLUMN IF NOT EXISTS staff_resolved_at  TIMESTAMPTZ;
ALTER TABLE calls ADD COLUMN IF NOT EXISTS sheet_synced       INT DEFAULT 0;
ALTER TABLE calls ADD COLUMN IF NOT EXISTS verified           INT DEFAULT 0;

COMMENT ON COLUMN calls.resolution_status IS 'resolved | partial | unresolved';
COMMENT ON COLUMN calls.satisfaction      IS 'happy | neutral | unhappy';
COMMENT ON COLUMN calls.verified          IS '1 only if two-factor caller verification passed';
COMMENT ON COLUMN calls.sheet_synced      IS '1 if the outcome row reached Google Sheets';

-- The two views ops actually opens: "what went badly" and "what needs a callback".
CREATE INDEX IF NOT EXISTS idx_calls_resolution
    ON calls (tenant_id, resolution_status);
CREATE INDEX IF NOT EXISTS idx_calls_followup
    ON calls (tenant_id, follow_up_required)
    WHERE follow_up_required = 1;


-- ---------------------------------------------------------------------
-- 3. suppliers — the same table holds both sides of the trade
-- ---------------------------------------------------------------------
ALTER TABLE suppliers ADD COLUMN IF NOT EXISTS contact_type VARCHAR(16) DEFAULT 'customer';

COMMENT ON COLUMN suppliers.contact_type IS
    'customer = they buy from us | supplier = they sell to us | both';

CREATE INDEX IF NOT EXISTS idx_suppliers_contact_type
    ON suppliers (tenant_id, contact_type);


-- ---------------------------------------------------------------------
-- 4. tenant_phone_numbers — which company did the caller dial?
-- ---------------------------------------------------------------------
-- Without this every inbound call falls through to a single default tenant,
-- which would serve one company's order data to another company's caller.
CREATE TABLE IF NOT EXISTS tenant_phone_numbers (
    phone_number VARCHAR(32) PRIMARY KEY,               -- E.164, e.g. +14155551234
    tenant_id    VARCHAR(64) NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    label        VARCHAR(128) DEFAULT '',
    active       INT DEFAULT 1,
    created_at   TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tenant_phone_numbers_tenant
    ON tenant_phone_numbers (tenant_id);


-- ---------------------------------------------------------------------
-- 5. Row-Level Security for the new table
-- ---------------------------------------------------------------------
ALTER TABLE tenant_phone_numbers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_policy ON tenant_phone_numbers;
CREATE POLICY tenant_isolation_policy ON tenant_phone_numbers
    FOR ALL
    USING (tenant_id = current_setting('app.current_tenant', true));


-- ---------------------------------------------------------------------
-- 6. Map your Twilio number to a tenant  <-- YOU MUST EDIT THIS
-- ---------------------------------------------------------------------
-- Replace the placeholder number with the Twilio number you bought, and
-- 'varun' with the tenant id it should serve. Until this row exists, calls
-- to that number fall back to DEFAULT_TENANT_ID and log a warning.
--
-- INSERT INTO tenant_phone_numbers (phone_number, tenant_id, label)
-- VALUES ('+14155551234', 'varun', 'Main support line')
-- ON CONFLICT (phone_number) DO UPDATE
--     SET tenant_id = EXCLUDED.tenant_id, label = EXCLUDED.label;


-- ---------------------------------------------------------------------
-- Verify the migration applied
-- ---------------------------------------------------------------------
-- SELECT column_name, data_type FROM information_schema.columns
--  WHERE table_name = 'calls' AND column_name IN
--        ('reason','solution','resolution_status','satisfaction','verified')
--  ORDER BY column_name;
