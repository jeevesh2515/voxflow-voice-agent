CREATE TABLE IF NOT EXISTS tenants (
	id VARCHAR(64) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	logo_url VARCHAR(512), 
	active INTEGER NOT NULL, 
	agent_name VARCHAR(64) NOT NULL, 
	system_prompt_override TEXT, 
	welcome_message TEXT, 
	default_language VARCHAR(8) NOT NULL, 
	webhook_url VARCHAR(512), 
	webhook_secret VARCHAR(128), 
	plan VARCHAR(32) NOT NULL, 
	total_minutes_used FLOAT NOT NULL, 
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
	auth_pin VARCHAR(16) NOT NULL, 
	contact_type VARCHAR(16) NOT NULL, 
	active INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_suppliers_contact_type ON suppliers (contact_type);

CREATE INDEX IF NOT EXISTS ix_suppliers_name ON suppliers (name);

CREATE INDEX IF NOT EXISTS ix_suppliers_phone ON suppliers (phone);

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
	recording_url VARCHAR(512), 
	verified INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	FOREIGN KEY(supplier_id) REFERENCES suppliers (id)
);

CREATE INDEX IF NOT EXISTS ix_calls_resolution_status ON calls (resolution_status);

CREATE INDEX IF NOT EXISTS ix_calls_satisfaction ON calls (satisfaction);

CREATE INDEX IF NOT EXISTS ix_calls_tenant_id ON calls (tenant_id);

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

CREATE INDEX IF NOT EXISTS ix_orders_supplier_id ON orders (supplier_id);

CREATE INDEX IF NOT EXISTS ix_orders_tenant_id ON orders (tenant_id);

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

CREATE INDEX IF NOT EXISTS ix_shipments_order_id ON shipments (order_id);

CREATE INDEX IF NOT EXISTS ix_shipments_tenant_id ON shipments (tenant_id);

-- ---------------------------------------------------------------------
-- 2. Row-Level Security
-- ---------------------------------------------------------------------
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

