CREATE TABLE IF NOT EXISTS provider_callback_quarantines (
	id VARCHAR(64) NOT NULL,
	provider VARCHAR(64) NOT NULL,
	provider_event_id VARCHAR(128) NOT NULL,
	provider_call_id VARCHAR(128) NOT NULL,
	event_type VARCHAR(64) NOT NULL,
	payload_hash VARCHAR(128) NOT NULL,
	reason_code VARCHAR(128) NOT NULL,
	received_at TIMESTAMP WITH TIME ZONE NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_provider_callback_quarantine_event UNIQUE (provider, provider_event_id)
);

CREATE INDEX IF NOT EXISTS ix_provider_callback_quarantine_created ON provider_callback_quarantines (created_at);

CREATE INDEX IF NOT EXISTS ix_provider_callback_quarantines_event_type ON provider_callback_quarantines (event_type);

CREATE INDEX IF NOT EXISTS ix_provider_callback_quarantines_provider ON provider_callback_quarantines (provider);

CREATE INDEX IF NOT EXISTS ix_provider_callback_quarantines_provider_call_id ON provider_callback_quarantines (provider_call_id);

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
	voice_persona VARCHAR(32) DEFAULT 'professional' NOT NULL,
	business_hours_enabled INTEGER DEFAULT 0 NOT NULL,
	business_hours_start VARCHAR(8) DEFAULT '09:00' NOT NULL,
	business_hours_end VARCHAR(8) DEFAULT '18:00' NOT NULL,
	business_hours_timezone VARCHAR(64) DEFAULT 'Asia/Kolkata' NOT NULL,
	business_days VARCHAR(64) DEFAULT 'mon,tue,wed,thu,fri' NOT NULL,
	out_of_hours_message TEXT,
	fallback_escalation_mode VARCHAR(32) DEFAULT 'human_callback' NOT NULL,
	fallback_phone VARCHAR(32),
	fallback_email VARCHAR(255),
	max_verification_failures INTEGER DEFAULT 3 NOT NULL,
	escalation_sla_minutes INTEGER DEFAULT 60 NOT NULL,
	google_sheet_id VARCHAR(128),
	google_sheet_name VARCHAR(255),
	google_sheet_tab VARCHAR(64) DEFAULT 'Call Log' NOT NULL,
	google_sheet_email_tab VARCHAR(64) DEFAULT 'Email Log' NOT NULL,
	google_sheet_connected_at TIMESTAMP WITH TIME ZONE,
	google_sheet_connected_by_user_id VARCHAR(128),
	google_sheet_status VARCHAR(32) DEFAULT 'disconnected' NOT NULL,
	call_retention_days INTEGER DEFAULT 90 NOT NULL,
	transcript_retention_days INTEGER DEFAULT 30 NOT NULL,
	pii_masking_enabled INTEGER DEFAULT 1 NOT NULL,
	data_residency_region VARCHAR(32) DEFAULT 'eu-west-2' NOT NULL,
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

CREATE TABLE IF NOT EXISTS drill_results (
	id VARCHAR(64) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	fixture_type VARCHAR(64) NOT NULL,
	fixture_version VARCHAR(32) NOT NULL,
	execution_key VARCHAR(128) NOT NULL,
	outcome VARCHAR(32) NOT NULL,
	evidence_json TEXT NOT NULL,
	recovery_summary VARCHAR(512) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_drill_result_execution UNIQUE (tenant_id, fixture_type, execution_key),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_drill_result_tenant_created ON drill_results (tenant_id, created_at);

CREATE INDEX IF NOT EXISTS ix_drill_result_tenant_fixture ON drill_results (tenant_id, fixture_type, created_at);

CREATE INDEX IF NOT EXISTS ix_drill_results_fixture_type ON drill_results (fixture_type);

CREATE INDEX IF NOT EXISTS ix_drill_results_outcome ON drill_results (outcome);

CREATE INDEX IF NOT EXISTS ix_drill_results_tenant_id ON drill_results (tenant_id);

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
	relay_owner VARCHAR(128),
	relay_lease_expires_at TIMESTAMP WITH TIME ZONE,
	publish_attempt INTEGER NOT NULL,
	last_error_code VARCHAR(128),
	last_error_json TEXT,
	PRIMARY KEY (id),
	CONSTRAINT uq_job_outbox_tenant_idempotency UNIQUE (tenant_id, idempotency_key),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_job_outbox_aggregate_id ON job_outbox (aggregate_id);

CREATE INDEX IF NOT EXISTS ix_job_outbox_claim ON job_outbox (published_at, relay_lease_expires_at, created_at);

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

CREATE TABLE IF NOT EXISTS pilot_cohort_members (
	id VARCHAR(64) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	cohort_id VARCHAR(96) NOT NULL,
	recipient_hash VARCHAR(64) NOT NULL,
	consent_evidence_ref VARCHAR(128) NOT NULL,
	status VARCHAR(32) NOT NULL,
	added_at TIMESTAMP WITH TIME ZONE NOT NULL,
	reviewed_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT uq_pilot_cohort_recipient UNIQUE (tenant_id, cohort_id, recipient_hash),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_pilot_cohort_member_lookup ON pilot_cohort_members (tenant_id, cohort_id, status);

CREATE INDEX IF NOT EXISTS ix_pilot_cohort_members_cohort_id ON pilot_cohort_members (cohort_id);

CREATE INDEX IF NOT EXISTS ix_pilot_cohort_members_recipient_hash ON pilot_cohort_members (recipient_hash);

CREATE INDEX IF NOT EXISTS ix_pilot_cohort_members_status ON pilot_cohort_members (status);

CREATE INDEX IF NOT EXISTS ix_pilot_cohort_members_tenant_id ON pilot_cohort_members (tenant_id);

CREATE TABLE IF NOT EXISTS pilot_configurations (
	tenant_id VARCHAR(64) NOT NULL,
	pilot_id VARCHAR(96) NOT NULL,
	version INTEGER NOT NULL,
	status VARCHAR(32) NOT NULL,
	cohort_id VARCHAR(96) NOT NULL,
	cohort_size INTEGER NOT NULL,
	timezone_name VARCHAR(64) NOT NULL,
	calling_window_start VARCHAR(5) NOT NULL,
	calling_window_end VARCHAR(5) NOT NULL,
	daily_call_limit INTEGER NOT NULL,
	max_in_flight INTEGER NOT NULL,
	expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
	primary_escalation_owner VARCHAR(255) NOT NULL,
	backup_escalation_owner VARCHAR(255) NOT NULL,
	acknowledgement_timeout_minutes INTEGER NOT NULL,
	metric_contract_version VARCHAR(32) NOT NULL,
	approved_by VARCHAR(255) NOT NULL,
	approved_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (tenant_id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_pilot_configurations_cohort_id ON pilot_configurations (cohort_id);

CREATE INDEX IF NOT EXISTS ix_pilot_configurations_expires_at ON pilot_configurations (expires_at);

CREATE UNIQUE INDEX IF NOT EXISTS ix_pilot_configurations_pilot_id ON pilot_configurations (pilot_id);

CREATE INDEX IF NOT EXISTS ix_pilot_configurations_status ON pilot_configurations (status);

CREATE TABLE IF NOT EXISTS pilot_operational_evidence (
	id VARCHAR(64) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	pilot_id VARCHAR(96) NOT NULL,
	pilot_version INTEGER NOT NULL,
	evidence_kind VARCHAR(32) NOT NULL,
	evidence_key VARCHAR(128) NOT NULL,
	decision VARCHAR(48) NOT NULL,
	reason_code VARCHAR(128) NOT NULL,
	snapshot_json TEXT NOT NULL,
	recorded_by VARCHAR(128) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_pilot_operational_evidence_key UNIQUE (tenant_id, pilot_id, pilot_version, evidence_kind, evidence_key),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_pilot_operational_evidence_decision ON pilot_operational_evidence (decision);

CREATE INDEX IF NOT EXISTS ix_pilot_operational_evidence_evidence_kind ON pilot_operational_evidence (evidence_kind);

CREATE INDEX IF NOT EXISTS ix_pilot_operational_evidence_pilot_id ON pilot_operational_evidence (pilot_id);

CREATE INDEX IF NOT EXISTS ix_pilot_operational_evidence_pilot_kind_created ON pilot_operational_evidence (pilot_id, evidence_kind, created_at);

CREATE INDEX IF NOT EXISTS ix_pilot_operational_evidence_tenant_created ON pilot_operational_evidence (tenant_id, created_at);

CREATE INDEX IF NOT EXISTS ix_pilot_operational_evidence_tenant_id ON pilot_operational_evidence (tenant_id);

CREATE TABLE IF NOT EXISTS pilot_security_incidents (
	id VARCHAR(64) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	pilot_id VARCHAR(96) NOT NULL,
	category VARCHAR(96) NOT NULL,
	severity VARCHAR(32) NOT NULL,
	status VARCHAR(32) NOT NULL,
	summary VARCHAR(512) NOT NULL,
	detected_at TIMESTAMP WITH TIME ZONE NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	resolved_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_pilot_security_incident_tenant_created ON pilot_security_incidents (tenant_id, created_at);

CREATE INDEX IF NOT EXISTS ix_pilot_security_incidents_category ON pilot_security_incidents (category);

CREATE INDEX IF NOT EXISTS ix_pilot_security_incidents_pilot_id ON pilot_security_incidents (pilot_id);

CREATE INDEX IF NOT EXISTS ix_pilot_security_incidents_severity ON pilot_security_incidents (severity);

CREATE INDEX IF NOT EXISTS ix_pilot_security_incidents_status ON pilot_security_incidents (status);

CREATE INDEX IF NOT EXISTS ix_pilot_security_incidents_tenant_id ON pilot_security_incidents (tenant_id);

CREATE TABLE IF NOT EXISTS privacy_requests (
	id VARCHAR(64) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	request_type VARCHAR(32) NOT NULL,
	subject_hash VARCHAR(64) NOT NULL,
	status VARCHAR(32) NOT NULL,
	requested_by VARCHAR(128) NOT NULL,
	review_note VARCHAR(512) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	reviewed_at TIMESTAMP WITH TIME ZONE,
	reviewed_by VARCHAR(128),
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_privacy_request_subject_hash ON privacy_requests (tenant_id, subject_hash);

CREATE INDEX IF NOT EXISTS ix_privacy_request_tenant_status ON privacy_requests (tenant_id, status);

CREATE INDEX IF NOT EXISTS ix_privacy_requests_request_type ON privacy_requests (request_type);

CREATE INDEX IF NOT EXISTS ix_privacy_requests_status ON privacy_requests (status);

CREATE INDEX IF NOT EXISTS ix_privacy_requests_tenant_id ON privacy_requests (tenant_id);

CREATE TABLE IF NOT EXISTS products (
	sku VARCHAR(64) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	name VARCHAR(255) NOT NULL,
	category VARCHAR(128) NOT NULL,
	pack_size VARCHAR(64) NOT NULL,
	mrp_inr FLOAT NOT NULL,
	PRIMARY KEY (sku, tenant_id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS provider_callback_adapter_audits (
	id VARCHAR(64) NOT NULL,
	tenant_id VARCHAR(64),
	provider VARCHAR(64) NOT NULL,
	provider_event_id VARCHAR(128) NOT NULL,
	provider_event_type VARCHAR(128),
	payload_hash VARCHAR(128) NOT NULL,
	verification_status VARCHAR(32) NOT NULL,
	normalization_status VARCHAR(32) NOT NULL,
	application_status VARCHAR(32) NOT NULL,
	reason_code VARCHAR(128),
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_provider_callback_adapter_audit_event_payload UNIQUE (provider, provider_event_id, payload_hash),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_provider_callback_adapter_audit_provider_created ON provider_callback_adapter_audits (provider, created_at);

CREATE INDEX IF NOT EXISTS ix_provider_callback_adapter_audit_tenant_created ON provider_callback_adapter_audits (tenant_id, created_at);

CREATE INDEX IF NOT EXISTS ix_provider_callback_adapter_audits_application_status ON provider_callback_adapter_audits (application_status);

CREATE INDEX IF NOT EXISTS ix_provider_callback_adapter_audits_normalization_status ON provider_callback_adapter_audits (normalization_status);

CREATE INDEX IF NOT EXISTS ix_provider_callback_adapter_audits_provider ON provider_callback_adapter_audits (provider);

CREATE INDEX IF NOT EXISTS ix_provider_callback_adapter_audits_provider_event_type ON provider_callback_adapter_audits (provider_event_type);

CREATE INDEX IF NOT EXISTS ix_provider_callback_adapter_audits_reason_code ON provider_callback_adapter_audits (reason_code);

CREATE INDEX IF NOT EXISTS ix_provider_callback_adapter_audits_tenant_id ON provider_callback_adapter_audits (tenant_id);

CREATE INDEX IF NOT EXISTS ix_provider_callback_adapter_audits_verification_status ON provider_callback_adapter_audits (verification_status);

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

CREATE TABLE IF NOT EXISTS recipient_campaign_preferences (
	id VARCHAR(64) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	recipient_phone VARCHAR(32) NOT NULL,
	consent_status VARCHAR(32) NOT NULL,
	consent_purpose VARCHAR(64) NOT NULL,
	opted_out INTEGER NOT NULL,
	source VARCHAR(128) NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_recipient_campaign_preference UNIQUE (tenant_id, recipient_phone),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_recipient_campaign_preferences_recipient_phone ON recipient_campaign_preferences (recipient_phone);

CREATE INDEX IF NOT EXISTS ix_recipient_campaign_preferences_tenant_id ON recipient_campaign_preferences (tenant_id);

CREATE TABLE IF NOT EXISTS reliability_slos (
	id VARCHAR(64) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	metric_type VARCHAR(64) NOT NULL,
	target_percent FLOAT NOT NULL,
	window_hours INTEGER NOT NULL,
	comparison VARCHAR(16) NOT NULL,
	active INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_reliability_slo_tenant_metric UNIQUE (tenant_id, metric_type),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_reliability_slo_tenant_active ON reliability_slos (tenant_id, active);

CREATE INDEX IF NOT EXISTS ix_reliability_slos_metric_type ON reliability_slos (metric_type);

CREATE INDEX IF NOT EXISTS ix_reliability_slos_tenant_id ON reliability_slos (tenant_id);

CREATE TABLE IF NOT EXISTS retention_purge_logs (
	id SERIAL NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	purged_by_user_id VARCHAR(128),
	execution_type VARCHAR(32) NOT NULL,
	records_scanned INTEGER NOT NULL,
	calls_anonymized INTEGER NOT NULL,
	transcripts_purged INTEGER NOT NULL,
	dry_run INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_retention_purge_logs_execution_type ON retention_purge_logs (execution_type);

CREATE INDEX IF NOT EXISTS ix_retention_purge_logs_tenant_created ON retention_purge_logs (tenant_id, created_at);

CREATE INDEX IF NOT EXISTS ix_retention_purge_logs_tenant_id ON retention_purge_logs (tenant_id);

CREATE TABLE IF NOT EXISTS stock (
	id SERIAL NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	sku VARCHAR(64) NOT NULL,
	warehouse VARCHAR(128) NOT NULL,
	quantity INTEGER NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_stock_sku ON stock (sku);

CREATE INDEX IF NOT EXISTS ix_stock_tenant_id ON stock (tenant_id);

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
	auth_pin VARCHAR(16),
	auth_pin_hash VARCHAR(255),
	pin_updated_at TIMESTAMP WITH TIME ZONE,
	pin_failed_attempts INTEGER DEFAULT 0 NOT NULL,
	pin_locked_until TIMESTAMP WITH TIME ZONE,
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

CREATE TABLE IF NOT EXISTS tenant_campaign_policies (
	tenant_id VARCHAR(64) NOT NULL,
	timezone_name VARCHAR(64) NOT NULL,
	calling_window_start VARCHAR(5) NOT NULL,
	calling_window_end VARCHAR(5) NOT NULL,
	daily_call_limit INTEGER NOT NULL,
	max_in_flight INTEGER NOT NULL,
	enabled INTEGER NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (tenant_id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE TABLE IF NOT EXISTS tenant_daily_dispatch_usage (
	id VARCHAR(96) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	local_date VARCHAR(10) NOT NULL,
	reserved_calls INTEGER NOT NULL,
	active_dispatches INTEGER NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_tenant_dispatch_usage_day UNIQUE (tenant_id, local_date),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_tenant_daily_dispatch_usage_local_date ON tenant_daily_dispatch_usage (local_date);

CREATE INDEX IF NOT EXISTS ix_tenant_daily_dispatch_usage_tenant_id ON tenant_daily_dispatch_usage (tenant_id);

CREATE TABLE IF NOT EXISTS tenant_members (
	id VARCHAR(64) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	user_id VARCHAR(128),
	subject_email_hash VARCHAR(64) NOT NULL,
	role VARCHAR(16) NOT NULL,
	status VARCHAR(16) NOT NULL,
	invited_by VARCHAR(128) NOT NULL,
	activated_at TIMESTAMP WITH TIME ZONE,
	revoked_at TIMESTAMP WITH TIME ZONE,
	revoked_by VARCHAR(128),
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_tenant_member_user UNIQUE (tenant_id, user_id),
	CONSTRAINT uq_tenant_member_email_hash UNIQUE (tenant_id, subject_email_hash),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_tenant_member_tenant_status ON tenant_members (tenant_id, status);

CREATE INDEX IF NOT EXISTS ix_tenant_member_user_status ON tenant_members (user_id, status);

CREATE INDEX IF NOT EXISTS ix_tenant_members_role ON tenant_members (role);

CREATE INDEX IF NOT EXISTS ix_tenant_members_status ON tenant_members (status);

CREATE INDEX IF NOT EXISTS ix_tenant_members_subject_email_hash ON tenant_members (subject_email_hash);

CREATE INDEX IF NOT EXISTS ix_tenant_members_tenant_id ON tenant_members (tenant_id);

CREATE INDEX IF NOT EXISTS ix_tenant_members_user_id ON tenant_members (user_id);

CREATE TABLE IF NOT EXISTS tenant_phone_numbers (
	phone_number VARCHAR(32) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	label VARCHAR(128) NOT NULL,
	provider VARCHAR(32) DEFAULT 'twilio' NOT NULL,
	verification_mode VARCHAR(16) DEFAULT 'standard' NOT NULL,
	route_language VARCHAR(16) DEFAULT 'tenant_default' NOT NULL,
	active INTEGER NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (phone_number),
	CONSTRAINT ck_tenant_phone_e164 CHECK (phone_number LIKE '+%%' AND length(phone_number) BETWEEN 9 AND 16),
	CONSTRAINT ck_tenant_phone_provider CHECK (provider IN ('connect', 'twilio', 'telnyx')),
	CONSTRAINT ck_tenant_phone_verification_mode CHECK (verification_mode IN ('standard', 'enhanced')),
	CONSTRAINT ck_tenant_phone_route_language CHECK (route_language IN ('tenant_default', 'en', 'hi')),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_tenant_phone_numbers_tenant_id ON tenant_phone_numbers (tenant_id);

CREATE INDEX IF NOT EXISTS ix_tenant_phone_provider_active ON tenant_phone_numbers (provider, phone_number, active);

CREATE INDEX IF NOT EXISTS ix_tenant_phone_tenant_active ON tenant_phone_numbers (tenant_id, active);

CREATE TABLE IF NOT EXISTS tenant_privacy_policies (
	tenant_id VARCHAR(64) NOT NULL,
	call_transcript_retention_days INTEGER NOT NULL,
	communication_retention_days INTEGER NOT NULL,
	recording_retention_days INTEGER NOT NULL,
	updated_by VARCHAR(128) NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (tenant_id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

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
	escalation_priority VARCHAR(16) DEFAULT 'medium' NOT NULL,
	escalation_status VARCHAR(16) DEFAULT 'none' NOT NULL,
	assigned_to_user_id VARCHAR(128),
	assigned_at TIMESTAMP WITH TIME ZONE,
	sla_due_at TIMESTAMP WITH TIME ZONE,
	resolved_by_user_id VARCHAR(128),
	resolution_category VARCHAR(64),
	sheet_synced INTEGER NOT NULL,
	avg_turn_latency_ms INTEGER NOT NULL,
	recording_url VARCHAR(512),
	verified INTEGER NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(supplier_id) REFERENCES suppliers (id)
);

CREATE INDEX IF NOT EXISTS ix_calls_escalation_status ON calls (escalation_status);

CREATE INDEX IF NOT EXISTS ix_calls_resolution_status ON calls (resolution_status);

CREATE INDEX IF NOT EXISTS ix_calls_satisfaction ON calls (satisfaction);

CREATE INDEX IF NOT EXISTS ix_calls_sla_due_at ON calls (sla_due_at);

CREATE INDEX IF NOT EXISTS ix_calls_tenant_id ON calls (tenant_id);

CREATE TABLE IF NOT EXISTS campaign_dispatch_reservations (
	id VARCHAR(64) NOT NULL,
	job_id VARCHAR(64) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	local_date VARCHAR(10) NOT NULL,
	status VARCHAR(32) NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	settled_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT uq_campaign_dispatch_reservation_job UNIQUE (job_id),
	FOREIGN KEY(job_id) REFERENCES job_runs (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX IF NOT EXISTS ix_campaign_dispatch_reservations_job_id ON campaign_dispatch_reservations (job_id);

CREATE INDEX IF NOT EXISTS ix_campaign_dispatch_reservations_local_date ON campaign_dispatch_reservations (local_date);

CREATE INDEX IF NOT EXISTS ix_campaign_dispatch_reservations_tenant_id ON campaign_dispatch_reservations (tenant_id);

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

CREATE TABLE IF NOT EXISTS provider_events (
	id VARCHAR(64) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	provider_operation_id VARCHAR(64) NOT NULL,
	provider VARCHAR(64) NOT NULL,
	provider_event_id VARCHAR(128) NOT NULL,
	provider_call_id VARCHAR(128) NOT NULL,
	event_type VARCHAR(64) NOT NULL,
	occurred_at TIMESTAMP WITH TIME ZONE NOT NULL,
	payload_hash VARCHAR(128) NOT NULL,
	normalized_payload_json TEXT NOT NULL,
	apply_status VARCHAR(32) NOT NULL,
	anomaly_code VARCHAR(128),
	applied_at TIMESTAMP WITH TIME ZONE NOT NULL,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_provider_events_provider_event UNIQUE (provider, provider_event_id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(provider_operation_id) REFERENCES provider_operations (id)
);

CREATE INDEX IF NOT EXISTS ix_provider_events_anomaly_code ON provider_events (anomaly_code);

CREATE INDEX IF NOT EXISTS ix_provider_events_apply_status ON provider_events (apply_status);

CREATE INDEX IF NOT EXISTS ix_provider_events_event_type ON provider_events (event_type);

CREATE INDEX IF NOT EXISTS ix_provider_events_occurred_at ON provider_events (occurred_at);

CREATE INDEX IF NOT EXISTS ix_provider_events_operation_occurred ON provider_events (provider_operation_id, occurred_at);

CREATE INDEX IF NOT EXISTS ix_provider_events_provider ON provider_events (provider);

CREATE INDEX IF NOT EXISTS ix_provider_events_provider_call_id ON provider_events (provider_call_id);

CREATE INDEX IF NOT EXISTS ix_provider_events_provider_operation_id ON provider_events (provider_operation_id);

CREATE INDEX IF NOT EXISTS ix_provider_events_tenant_created ON provider_events (tenant_id, created_at);

CREATE INDEX IF NOT EXISTS ix_provider_events_tenant_id ON provider_events (tenant_id);

CREATE TABLE IF NOT EXISTS side_effect_intents (
	id VARCHAR(64) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	job_id VARCHAR(64) NOT NULL,
	effect_type VARCHAR(128) NOT NULL,
	aggregate_type VARCHAR(128) NOT NULL,
	aggregate_id VARCHAR(64) NOT NULL,
	idempotency_key VARCHAR(255) NOT NULL,
	payload_hash VARCHAR(64) NOT NULL,
	status VARCHAR(32) NOT NULL,
	result_code VARCHAR(128),
	result_json TEXT,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
	completed_at TIMESTAMP WITH TIME ZONE,
	PRIMARY KEY (id),
	CONSTRAINT uq_side_effect_intent_idempotency UNIQUE (tenant_id, idempotency_key),
	CONSTRAINT uq_side_effect_intent_job UNIQUE (job_id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(job_id) REFERENCES job_runs (id)
);

CREATE INDEX IF NOT EXISTS ix_side_effect_intent_tenant_type_status ON side_effect_intents (tenant_id, effect_type, status, created_at);

CREATE INDEX IF NOT EXISTS ix_side_effect_intents_aggregate_id ON side_effect_intents (aggregate_id);

CREATE INDEX IF NOT EXISTS ix_side_effect_intents_effect_type ON side_effect_intents (effect_type);

CREATE INDEX IF NOT EXISTS ix_side_effect_intents_job_id ON side_effect_intents (job_id);

CREATE INDEX IF NOT EXISTS ix_side_effect_intents_status ON side_effect_intents (status);

CREATE INDEX IF NOT EXISTS ix_side_effect_intents_tenant_id ON side_effect_intents (tenant_id);

CREATE TABLE IF NOT EXISTS campaign_policy_decisions (
	id VARCHAR(64) NOT NULL,
	tenant_id VARCHAR(64) NOT NULL,
	job_id VARCHAR(64) NOT NULL,
	campaign_id VARCHAR(64) NOT NULL,
	campaign_queue_id VARCHAR(64) NOT NULL,
	decision VARCHAR(32) NOT NULL,
	reason_code VARCHAR(128) NOT NULL,
	evidence_json TEXT NOT NULL,
	next_eligible_at TIMESTAMP WITH TIME ZONE,
	created_at TIMESTAMP WITH TIME ZONE NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(tenant_id) REFERENCES tenants (id),
	FOREIGN KEY(job_id) REFERENCES job_runs (id),
	FOREIGN KEY(campaign_id) REFERENCES outbound_campaigns (id),
	FOREIGN KEY(campaign_queue_id) REFERENCES campaign_queue (id)
);

CREATE INDEX IF NOT EXISTS ix_campaign_policy_decision_target ON campaign_policy_decisions (tenant_id, campaign_queue_id, created_at);

CREATE INDEX IF NOT EXISTS ix_campaign_policy_decisions_campaign_id ON campaign_policy_decisions (campaign_id);

CREATE INDEX IF NOT EXISTS ix_campaign_policy_decisions_campaign_queue_id ON campaign_policy_decisions (campaign_queue_id);

CREATE INDEX IF NOT EXISTS ix_campaign_policy_decisions_decision ON campaign_policy_decisions (decision);

CREATE INDEX IF NOT EXISTS ix_campaign_policy_decisions_job_id ON campaign_policy_decisions (job_id);

CREATE INDEX IF NOT EXISTS ix_campaign_policy_decisions_reason_code ON campaign_policy_decisions (reason_code);

CREATE INDEX IF NOT EXISTS ix_campaign_policy_decisions_tenant_id ON campaign_policy_decisions (tenant_id);

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

