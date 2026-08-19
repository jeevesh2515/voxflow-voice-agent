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

CREATE TABLE IF NOT EXISTS agent_states (
	key VARCHAR(128) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	value_json TEXT NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (key),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_agent_states_tenant_id ON agent_states (tenant_id);

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

CREATE TABLE IF NOT EXISTS job_outbox (
	id VARCHAR(64) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	event_type VARCHAR(128) NOT NULL,
	aggregate_type VARCHAR(128) NOT NULL,
	aggregate_id VARCHAR(64) NOT NULL,
	payload_json TEXT NOT NULL,
	idempotency_key VARCHAR(255) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	published_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT uq_job_outbox_tenant_idempotency UNIQUE (tenant_id, idempotency_key),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_job_outbox_aggregate_id ON job_outbox (aggregate_id);

CREATE INDEX IF NOT EXISTS ix_job_outbox_event_type ON job_outbox (event_type);

CREATE INDEX IF NOT EXISTS ix_job_outbox_tenant_id ON job_outbox (tenant_id);

CREATE INDEX IF NOT EXISTS ix_job_outbox_unpublished ON job_outbox (published_at, created_at);

CREATE TABLE IF NOT EXISTS job_runs (
	id VARCHAR(64) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
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
	PRIMARY KEY (id),
	CONSTRAINT uq_job_runs_tenant_idempotency UNIQUE (tenant_id, idempotency_key),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_job_runs_claim ON job_runs (status, next_run_at, priority, scheduled_at);

CREATE INDEX IF NOT EXISTS ix_job_runs_job_type ON job_runs (job_type);

CREATE INDEX IF NOT EXISTS ix_job_runs_lease ON job_runs (lease_expires_at);

CREATE INDEX IF NOT EXISTS ix_job_runs_status ON job_runs (status);

CREATE INDEX IF NOT EXISTS ix_job_runs_tenant_id ON job_runs (tenant_id);

CREATE INDEX IF NOT EXISTS ix_job_runs_trace_id ON job_runs (trace_id);

CREATE TABLE IF NOT EXISTS outbound_campaigns (
	id VARCHAR(64) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	name VARCHAR(255) NOT NULL,
	campaign_type VARCHAR(64) NOT NULL,
	status VARCHAR(32) NOT NULL,
	total_targets INTEGER NOT NULL,
	successful_calls INTEGER NOT NULL,
	failed_calls INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_outbound_campaigns_tenant_id ON outbound_campaigns (tenant_id);

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

CREATE TABLE IF NOT EXISTS provider_operations (
	id VARCHAR(64) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	provider VARCHAR(64) NOT NULL,
	operation_type VARCHAR(64) NOT NULL,
	idempotency_key VARCHAR(255) NOT NULL,
	provider_id VARCHAR(128),
	request_hash VARCHAR(128),
	status VARCHAR(32) NOT NULL,
	requested_at TIMESTAMP WITH TIME ZONE NOT NULL,
	confirmed_at TIMESTAMP WITH TIME ZONE,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_provider_operations_idempotency UNIQUE (tenant_id, provider, operation_type, idempotency_key),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_provider_operations_operation_type ON provider_operations (operation_type);

CREATE INDEX IF NOT EXISTS ix_provider_operations_provider ON provider_operations (provider);

CREATE INDEX IF NOT EXISTS ix_provider_operations_provider_id ON provider_operations (provider_id);

CREATE INDEX IF NOT EXISTS ix_provider_operations_status ON provider_operations (status);

CREATE INDEX IF NOT EXISTS ix_provider_operations_tenant_id ON provider_operations (tenant_id);

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

CREATE TABLE IF NOT EXISTS campaign_queue (
	id VARCHAR(64) NOT NULL,
	campaign_id VARCHAR(64) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	recipient_phone VARCHAR(32) NOT NULL,
	recipient_name VARCHAR(255) NOT NULL,
	context_data_json TEXT NOT NULL,
	status VARCHAR(32) NOT NULL,
	attempts_made INTEGER NOT NULL,
	max_attempts INTEGER NOT NULL,
	next_retry_at TIMESTAMP WITH TIME ZONE,
	call_id VARCHAR(64),
	transcript_summary TEXT,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(campaign_id) REFERENCES outbound_campaigns (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_campaign_queue_campaign_id ON campaign_queue (campaign_id);

CREATE INDEX IF NOT EXISTS ix_campaign_queue_tenant_id ON campaign_queue (tenant_id);

CREATE TABLE IF NOT EXISTS job_attempts (
	id VARCHAR(64) NOT NULL,
	job_id VARCHAR(64) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	attempt_no INTEGER NOT NULL,
	worker_id VARCHAR(128) NOT NULL,
	outcome VARCHAR(32) NOT NULL,
	provider_request_id VARCHAR(128),
	error_code VARCHAR(128),
	error_json TEXT,
	started_at TIMESTAMP WITH TIME ZONE NOT NULL,
	finished_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT uq_job_attempts_job_attempt UNIQUE (job_id, attempt_no),
	FOREIGN KEY(job_id) REFERENCES job_runs (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_job_attempts_job_id ON job_attempts (job_id);

CREATE INDEX IF NOT EXISTS ix_job_attempts_tenant_id ON job_attempts (tenant_id);

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
ALTER TABLE agent_states ENABLE ROW LEVEL SECURITY;
ALTER TABLE outbound_campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_outbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE provider_operations ENABLE ROW LEVEL SECURITY;

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
DROP POLICY IF EXISTS tenant_isolation_policy ON agent_states;
CREATE POLICY tenant_isolation_policy ON agent_states
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON outbound_campaigns;
CREATE POLICY tenant_isolation_policy ON outbound_campaigns
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
DROP POLICY IF EXISTS tenant_isolation_policy ON campaign_queue;
CREATE POLICY tenant_isolation_policy ON campaign_queue
    FOR ALL USING (tenant_id = current_setting('app.current_tenant', true));
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

