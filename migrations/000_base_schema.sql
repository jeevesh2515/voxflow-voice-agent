-- =====================================================================
-- VoxFlow 000 — complete base schema
-- =====================================================================
--
-- Run this ONCE in the Supabase dashboard: SQL Editor -> New query ->
-- paste -> Run. Then run migrations/001_customer_support_flow.sql, which
-- is a no-op on a database created by this file (every statement is
-- IF NOT EXISTS) but is needed for databases created before it existed.
--
-- Safe to re-run. Every statement is idempotent.
--
-- WHY THIS FILE EXISTS
-- --------------------
-- The DDL used to live only in schema.md, as prose-wrapped code fences that
-- had to be copied out by hand, in the right order, in two pieces. Hand-copied
-- DDL drifts from the ORM the moment either side changes, and the drift is
-- silent until a query fails at runtime.
--
-- This file is GENERATED FROM THE SQLAlchemy MODELS in voxflow_api/db.py, so
-- it cannot disagree with the code that queries it. Regenerate with:
--
--     python -m voxflow_api.gen_schema > migrations/000_base_schema.sql
--
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. Tables and indexes
-- ---------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS tenants (
	id VARCHAR(64) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	logo_url VARCHAR(512), 
	active INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ix_tenants_name ON tenants (name);

CREATE TABLE IF NOT EXISTS communication_logs (
	id VARCHAR(64) NOT NULL, 
	tenant_id VARCHAR(64) NOT NULL, 
	channel VARCHAR(32) NOT NULL, 
	recipient VARCHAR(255) NOT NULL, 
	subject VARCHAR(255), 
	body TEXT NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_communication_logs_tenant_id ON communication_logs (tenant_id);

CREATE TABLE IF NOT EXISTS products (
	sku VARCHAR(64) NOT NULL, 
	tenant_id VARCHAR(64) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	category VARCHAR(128) NOT NULL, 
	pack_size VARCHAR(64) NOT NULL, 
	mrp_inr FLOAT NOT NULL, 
	PRIMARY KEY (sku), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_products_tenant_id ON products (tenant_id);

CREATE TABLE IF NOT EXISTS suppliers (
	id VARCHAR(64) NOT NULL, 
	tenant_id VARCHAR(64) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	phone VARCHAR(32) NOT NULL, 
	city VARCHAR(128) NOT NULL, 
	state VARCHAR(128) NOT NULL, 
	pincode VARCHAR(16) NOT NULL, 
	contact_person VARCHAR(255) NOT NULL, 
	gstin VARCHAR(32) NOT NULL, 
	contact_type VARCHAR(16) NOT NULL, 
	active INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_suppliers_phone ON suppliers (phone);

CREATE INDEX IF NOT EXISTS ix_suppliers_name ON suppliers (name);

CREATE INDEX IF NOT EXISTS ix_suppliers_contact_type ON suppliers (contact_type);

CREATE INDEX IF NOT EXISTS ix_suppliers_tenant_id ON suppliers (tenant_id);

CREATE TABLE IF NOT EXISTS tenant_phone_numbers (
	phone_number VARCHAR(32) NOT NULL, 
	tenant_id VARCHAR(64) NOT NULL, 
	label VARCHAR(128) NOT NULL, 
	active INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (phone_number), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_tenant_phone_numbers_tenant_id ON tenant_phone_numbers (tenant_id);

CREATE TABLE IF NOT EXISTS worksheet_logs (
	id SERIAL NOT NULL, 
	tenant_id VARCHAR(64) NOT NULL, 
	worksheet_name VARCHAR(128) NOT NULL, 
	action_type VARCHAR(32) NOT NULL, 
	row_data_json TEXT NOT NULL, 
	timestamp TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_worksheet_logs_tenant_id ON worksheet_logs (tenant_id);

CREATE TABLE IF NOT EXISTS appointments (
	id VARCHAR(64) NOT NULL, 
	tenant_id VARCHAR(64) NOT NULL, 
	supplier_id VARCHAR(64), 
	datetime TIMESTAMP WITH TIME ZONE NOT NULL, 
	purpose TEXT NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(supplier_id) REFERENCES suppliers (id)
);

CREATE INDEX IF NOT EXISTS ix_appointments_tenant_id ON appointments (tenant_id);

CREATE TABLE IF NOT EXISTS calls (
	id VARCHAR(64) NOT NULL, 
	tenant_id VARCHAR(64) NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	ended_at TIMESTAMP WITH TIME ZONE, 
	duration_sec INTEGER NOT NULL, 
	supplier_id VARCHAR(64), 
	caller_phone VARCHAR(32) NOT NULL, 
	caller_name VARCHAR(255) NOT NULL, 
	language VARCHAR(8) NOT NULL, 
	intent VARCHAR(64) NOT NULL, 
	outcome VARCHAR(64) NOT NULL, 
	escalated INTEGER NOT NULL, 
	transcript_json TEXT NOT NULL, 
	actions_json TEXT NOT NULL, 
	reason TEXT NOT NULL, 
	solution TEXT NOT NULL, 
	resolution_status VARCHAR(16) NOT NULL, 
	satisfaction VARCHAR(16) NOT NULL, 
	follow_up_required INTEGER NOT NULL, 
	staff_resolution TEXT NOT NULL, 
	staff_resolved_at TIMESTAMP WITH TIME ZONE, 
	sheet_synced INTEGER NOT NULL, 
	verified INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(supplier_id) REFERENCES suppliers (id)
);

CREATE INDEX IF NOT EXISTS ix_calls_satisfaction ON calls (satisfaction);

CREATE INDEX IF NOT EXISTS ix_calls_tenant_id ON calls (tenant_id);

CREATE INDEX IF NOT EXISTS ix_calls_resolution_status ON calls (resolution_status);

CREATE TABLE IF NOT EXISTS orders (
	id VARCHAR(64) NOT NULL, 
	tenant_id VARCHAR(64) NOT NULL, 
	supplier_id VARCHAR(64) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	items_json TEXT NOT NULL, 
	total_qty INTEGER NOT NULL, 
	notes TEXT NOT NULL, 
	customer_po_ref VARCHAR(128) NOT NULL, 
	po_signed INTEGER NOT NULL, 
	po_signed_at TIMESTAMP WITH TIME ZONE, 
	po_signed_by VARCHAR(255) NOT NULL, 
	dispatched_at TIMESTAMP WITH TIME ZONE, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(supplier_id) REFERENCES suppliers (id)
);

CREATE INDEX IF NOT EXISTS ix_orders_customer_po_ref ON orders (customer_po_ref);

CREATE INDEX IF NOT EXISTS ix_orders_tenant_id ON orders (tenant_id);

CREATE INDEX IF NOT EXISTS ix_orders_supplier_id ON orders (supplier_id);

CREATE TABLE IF NOT EXISTS stock (
	id SERIAL NOT NULL, 
	tenant_id VARCHAR(64) NOT NULL, 
	sku VARCHAR(64) NOT NULL, 
	warehouse VARCHAR(128) NOT NULL, 
	quantity INTEGER NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(sku) REFERENCES products (sku)
);

CREATE INDEX IF NOT EXISTS ix_stock_sku ON stock (sku);

CREATE INDEX IF NOT EXISTS ix_stock_tenant_id ON stock (tenant_id);

CREATE TABLE IF NOT EXISTS shipments (
	id VARCHAR(64) NOT NULL, 
	tenant_id VARCHAR(64) NOT NULL, 
	order_id VARCHAR(64) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	carrier VARCHAR(128) NOT NULL, 
	tracking_no VARCHAR(128) NOT NULL, 
	expected_delivery TIMESTAMP WITH TIME ZONE, 
	last_update TIMESTAMP WITH TIME ZONE NOT NULL, 
	history_json TEXT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(order_id) REFERENCES orders (id)
);

CREATE INDEX IF NOT EXISTS ix_shipments_tenant_id ON shipments (tenant_id);

CREATE INDEX IF NOT EXISTS ix_shipments_order_id ON shipments (order_id);


-- ---------------------------------------------------------------------
-- 2. Row-Level Security
-- ---------------------------------------------------------------------
--
-- This matters more than it looks. The Supabase project ref is effectively
-- public (it appears in this repository's git history), and the anon key is
-- public by design. Without RLS, anyone who knows the ref can read every row
-- in this database through the auto-generated PostgREST API at
--     https://<ref>.supabase.co/rest/v1/orders
--
-- With RLS on and no policy granting access to `anon`, that request returns
-- an empty array.
--
-- This does NOT affect the application. VoxFlow connects as the `postgres`
-- role, which owns these tables, and in Postgres a table owner bypasses RLS
-- unless FORCE ROW LEVEL SECURITY is set. Tenant isolation for the app is
-- enforced in the query layer (every statement filters on tenant_id), which
-- is where it has always been enforced.

ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE suppliers ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE shipments ENABLE ROW LEVEL SECURITY;
ALTER TABLE calls ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE worksheet_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE communication_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenant_phone_numbers ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_policy ON suppliers;
CREATE POLICY tenant_isolation_policy ON suppliers
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON products;
CREATE POLICY tenant_isolation_policy ON products
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON stock;
CREATE POLICY tenant_isolation_policy ON stock
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON orders;
CREATE POLICY tenant_isolation_policy ON orders
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON shipments;
CREATE POLICY tenant_isolation_policy ON shipments
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON calls;
CREATE POLICY tenant_isolation_policy ON calls
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON appointments;
CREATE POLICY tenant_isolation_policy ON appointments
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON worksheet_logs;
CREATE POLICY tenant_isolation_policy ON worksheet_logs
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON communication_logs;
CREATE POLICY tenant_isolation_policy ON communication_logs
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON tenant_phone_numbers;
CREATE POLICY tenant_isolation_policy ON tenant_phone_numbers
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));

-- ---------------------------------------------------------------------
-- 3. Composite indexes for the queries a live call actually runs
-- ---------------------------------------------------------------------
-- The model-level indexes above are single-column. These match the real
-- access patterns, which are always tenant-scoped.

CREATE INDEX IF NOT EXISTS idx_orders_customer_po_ref ON orders (tenant_id, customer_po_ref);
CREATE INDEX IF NOT EXISTS idx_calls_resolution       ON calls  (tenant_id, resolution_status);
CREATE INDEX IF NOT EXISTS idx_calls_followup         ON calls  (tenant_id, follow_up_required)
    WHERE follow_up_required = 1;
CREATE INDEX IF NOT EXISTS idx_suppliers_contact_type ON suppliers (tenant_id, contact_type);


-- ---------------------------------------------------------------------
-- 4. Verify
-- ---------------------------------------------------------------------
-- Expect 11 rows.
--
--   SELECT table_name FROM information_schema.tables
--    WHERE table_schema = 'public' ORDER BY table_name;
