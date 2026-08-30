// Shared types between the dashboard and the API.

export interface Summary {
  suppliers: number;
  orders: number;
  calls: number;
  last_call_at: string | null;
  pending_orders: number;
}

export interface Supplier {
  id: string;
  name: string;
  phone: string;
  city: string;
  state: string;
  pincode: string;
  contact_person: string;
  gstin: string;
}

export interface StockItem {
  sku: string;
  name: string;
  warehouse: string;
  quantity: number;
  pack_size: string;
  mrp_inr: number;
}

export interface OrderItem {
  sku: string;
  quantity: number;
}

export interface Order {
  id: string;
  supplier_id: string;
  status: string;
  items: OrderItem[];
  total_qty: number;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface Shipment {
  id: string;
  order_id: string;
  status: string;
  carrier: string;
  tracking_no: string;
  expected_delivery: string | null;
  last_update: string;
  history: Array<{ at: string; status: string; note: string }>;
}

export interface CallTurn {
  role: "caller" | "agent";
  text: string;
  at: string;
}

export interface CallAction {
  name: string;
  args: Record<string, any>;
  result?: any;
  at: string;
}

export type ResolutionStatus = "resolved" | "partial" | "unresolved" | "";
export type Satisfaction = "happy" | "neutral" | "unhappy" | "";
export type EscalationPriority = "critical" | "high" | "medium" | "low";
export type EscalationStatus = "none" | "pending" | "in_progress" | "resolved" | "dismissed";
export type ResolutionCategory =
  | "callback_completed"
  | "order_updated"
  | "refund_issued"
  | "quote_sent"
  | "technical_fixed"
  | "duplicate_or_invalid"
  | "other";

export interface Call {
  id: string;
  started_at: string;
  ended_at: string | null;
  duration_sec: number;
  supplier_id: string | null;
  caller_phone: string;
  caller_name: string;
  language: string;
  intent: string;
  outcome: string;
  escalated: boolean;
  transcript: CallTurn[];
  actions: CallAction[];
  // Structured call-outcome fields (may be empty string/null for old rows)
  reason: string;
  solution: string;
  summary?: string;
  resolution_status: ResolutionStatus;
  satisfaction: Satisfaction;
  follow_up_required: boolean;
  staff_resolution: string;
  staff_resolved_at: string | null;
  escalation_priority?: EscalationPriority;
  escalation_status?: EscalationStatus;
  assigned_to_user_id?: string | null;
  assigned_at?: string | null;
  sla_due_at?: string | null;
  resolved_by_user_id?: string | null;
  resolution_category?: ResolutionCategory | string | null;
  sheet_synced: boolean;
  verified: boolean;
  recording_url?: string | null;
}

export interface EscalationMetrics {
  tenant_id: string;
  total_escalations: number;
  open_count: number;
  pending_count: number;
  in_progress_count: number;
  resolved_count: number;
  dismissed_count: number;
  breached_count: number;
  sla_compliance_rate: number;
  avg_resolution_min: number;
}

export interface EscalationsListResponse {
  items: Call[];
  total: number;
  limit: number;
  offset: number;
}

export interface OutboundCampaign {
  id: string;
  tenant_id: string;
  name: string;
  campaign_type: string;
  status: "draft" | "active" | "running" | "paused" | "completed";
  total_targets: number;
  successful_calls: number;
  failed_calls: number;
  created_at: string;
  updated_at: string;
}

export interface CampaignQueueItem {
  id: string;
  recipient_phone: string;
  recipient_name: string;
  status: "queued" | "dialing" | "answered" | "no_answer" | "completed" | "failed" | "cancelled";
  attempts_made: number;
  call_id?: string | null;
  transcript_summary?: string | null;
  updated_at: string;
}


export interface JobHealth {
  tenant_id: string;
  activation_mode: "staged" | "dry_run" | "canary";
  rollout: {
    canary_allowed: boolean;
    dry_run: boolean;
  };
  status_counts: Record<string, number>;
  active_leases: number;
  expired_leases: number;
  oldest_ready_at: string | null;
  outbox: {
    unpublished: number;
    oldest_unpublished_at: string | null;
  };
}

export interface AnalyticsAlert {
  level: "info" | "warning" | "critical";
  code: string;
  message: string;
}

export interface AnalyticsTrendPoint {
  date: string;
  calls: number;
  resolved: number;
  escalated: number;
  duration_sec: number;
}

export interface AnalyticsOverview {
  tenant: {
    id: string;
    name: string;
    plan: string;
  };
  period: {
    days: number;
    from: string;
    to: string;
    generated_at: string;
  };
  kpis: {
    total_calls: number;
    resolved_calls: number;
    resolution_rate: number;
    escalated_calls: number;
    escalation_rate: number;
    open_follow_ups: number;
    verified_call_rate: number;
    average_handle_time_sec: number;
    total_duration_sec: number;
    total_minutes: number;
  };
  trends: AnalyticsTrendPoint[];
  distribution: {
    intents: Record<string, number>;
    outcomes: Record<string, number>;
    satisfaction: Record<string, number>;
    languages: Record<string, number>;
  };
  campaigns: {
    total_campaigns: number;
    status_counts: Record<string, number>;
    target_status_counts: Record<string, number>;
    policy_decision_counts: Record<string, number>;
    policy_reason_counts: Record<string, number>;
  };
  provider_lifecycle: {
    event_count: number;
    event_type_counts: Record<string, number>;
    apply_status_counts: Record<string, number>;
    anomaly_count: number;
  };
  dial_sandbox_adapter: {
    adapter_enabled: boolean;
    sandbox_mode: boolean;
    tenant_allowed: boolean;
    audit_count: number;
    verification_status_counts: Record<string, number>;
    normalization_status_counts: Record<string, number>;
    application_status_counts: Record<string, number>;
    verification_failure_count: number;
    blocked_application_count: number;
  };
  durable_side_effects: {
    activation_mode: "staged" | "blocked" | "dry_run" | "canary";
    dry_run: boolean;
    tenant_allowed: boolean;
    intent_count: number;
    pending_count: number;
    error_count: number;
    type_counts: Record<string, number>;
    status_counts: Record<string, number>;
  };
  monitoring: {
    state: "healthy" | "attention" | "critical";
    alerts: AnalyticsAlert[];
    job_status_counts: Record<string, number>;
    active_jobs: number;
    expired_leases: number;
    dead_lettered_jobs: number;
    jobs_with_error_evidence: number;
    oldest_ready_age_sec: number | null;
    unpublished_outbox: number;
    oldest_outbox_age_sec: number | null;
    rollout: {
      activation_mode: "staged" | "dry_run" | "canary";
      canary_allowed: boolean;
      dry_run: boolean;
    };
  };
}

export interface JobSummary {
  id: string;
  job_type: string;
  status: string;
  attempt: number;
  max_attempts: number;
  priority: number;
  next_run_at: string | null;
  lease_owner: string | null;
  lease_expires_at: string | null;
  last_error_code: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PilotReadinessMetric {
  numerator?: number;
  denominator?: number;
  rate?: number | null;
  confirmed_count?: number;
  objective?: number;
}

export interface PilotReadiness {
  tenant_id: string;
  configured: boolean;
  pilot?: {
    pilot_id: string;
    version: number;
    status: string;
    cohort_id: string;
    cohort_size: number;
    approved_member_count: number;
    timezone_name: string;
    calling_window_start: string;
    calling_window_end: string;
    daily_call_limit: number;
    max_in_flight: number;
    expires_at: string;
    primary_escalation_owner: string;
    backup_escalation_owner: string;
    acknowledgement_timeout_minutes: number;
    metric_contract_version: string;
    approved_by: string;
  };
  readiness: {
    state: "blocked" | "ready_for_review";
    blocking_reasons: string[];
    workers?: {
      campaign_worker_enabled: boolean;
      campaign_dry_run: boolean;
      side_effect_worker_enabled: boolean;
      side_effect_dry_run: boolean;
    };
  };
  metric_contract: Record<string, { formula: string; denominator: string; exclusions: string; source: string }>;
  metrics: {
    successful_call_completion?: PilotReadinessMetric;
    escalation_rate?: PilotReadinessMetric;
    first_call_resolution?: PilotReadinessMetric;
    security_incidents?: PilotReadinessMetric;
  };
  rollback: {
    configured: boolean;
    can_execute: boolean;
    active_claim_count?: number;
    would_cancel_job_count?: number;
    worker_disabled?: boolean;
    reason?: string;
  };
}

export interface PilotOperationsEvidence {
  evidence_kind: "preflight" | "hold_point" | "pause" | "rollback";
  evidence_key: string;
  decision: "continue_same_cohort" | "pause" | "rollback_requested" | "blocked";
  reason_code: string;
  recorded_by: string;
  created_at: string;
}

export interface PilotOperations {
  tenant_id: string;
  configured: boolean;
  pilot?: {
    pilot_id: string;
    version: number;
    status: string;
    cohort_id: string;
    cohort_size: number;
    timezone_name: string;
    calling_window_start: string;
    calling_window_end: string;
    expires_at: string;
    metric_contract_version: string;
  };
  preflight: {
    state: "blocked" | "review_required";
    blocking_reasons: string[];
    no_auto_expansion: boolean;
    requires_human_hold_point: boolean;
    current_local_operating_day?: string;
  };
  workers?: {
    campaign_worker_enabled: boolean;
    campaign_dry_run: boolean;
    side_effect_worker_enabled: boolean;
    side_effect_dry_run: boolean;
  };
  queue: {
    campaign_ready_or_retrying: number;
    campaign_running: number;
    campaign_dead_lettered: number;
    campaign_expired_leases: number;
    all_tenant_running: number;
  };
  callbacks: {
    signed_callback_events: number;
    callback_anomalies: number;
    adapter_audits: number;
    adapter_verification_failures: number;
    adapter_blocked_applications: number;
  };
  side_effects: {
    intent_count: number;
    pending_count: number;
    error_count: number;
  };
  latest_evidence: PilotOperationsEvidence | null;
  hold_point?: {
    state: "blocked" | "reviewed_same_cohort";
    decision: PilotOperationsEvidence["decision"] | null;
    reason: string;
    fresh_for_current_operating_day: boolean;
    expansion_permitted: false;
    same_cohort_only: true;
    latest_evidence: PilotOperationsEvidence | null;
  };
}

export interface ReliabilitySLO {
  id: string | null;
  metric_type: string;
  label: string;
  target_percent: number;
  window_hours: number;
  comparison: "minimum" | "maximum" | string;
  source: "built_in_contract" | "tenant_configuration" | string;
  actual_percent: number | null;
  sample_size: number;
  status: "passing" | "failing" | "insufficient_evidence";
  evidence: Record<string, unknown>;
}

export interface ReliabilityScorecard {
  tenant_id: string;
  generated_at: string;
  read_only: true;
  summary: {
    state: "healthy" | "attention" | "blocked";
    passing_count: number;
    failing_count: number;
    insufficient_evidence_count: number;
  };
  slos: ReliabilitySLO[];
  safety_guardrails: {
    campaign_worker_enabled: boolean;
    campaign_dry_run: boolean;
    side_effect_worker_enabled: boolean;
    side_effect_dry_run: boolean;
    safe: boolean;
    external_actions: 0;
    worker_activation_available: false;
    provider_access_available: false;
  };
}

export interface DrillResult {
  id: string;
  fixture_type: "expired_lease" | "dead_letter" | "callback_anomaly" | "pause" | "stale_evidence" | "version_drift" | string;
  fixture_version: string;
  outcome: "passed" | "failed" | "blocked";
  recovery_summary: string;
  created_at: string;
  evidence: {
    expected_blocking_reason?: string;
    observed_signals?: Record<string, unknown>;
    detected?: boolean;
    external_actions?: 0;
    created_job_rows?: 0;
    created_provider_operations?: 0;
    provider_requests?: 0;
  };
}

export interface DrillResultsResponse {
  tenant_id: string;
  read_only: true;
  results: DrillResult[];
}

export interface RecoveryPreview {
  tenant_id: string;
  generated_at: string;
  read_only: true;
  can_execute_from_browser: false;
  external_actions: 0;
  worker_activation_available: false;
  provider_access_available: false;
  safety_posture: {
    campaign_worker_enabled: boolean;
    campaign_dry_run: boolean;
    side_effect_worker_enabled: boolean;
    side_effect_dry_run: boolean;
    safe: boolean;
  };
  preflight_state: "blocked" | "review_required" | string;
  hold_point_state: "blocked" | "reviewed_same_cohort" | string;
  rollback: {
    configured: boolean;
    can_execute: false;
    would_cancel_job_count: number;
    active_claim_count: number;
    execution_guard: string;
  };
  recommended_actions: Array<{
    priority: number;
    condition: string;
    action: string;
    execution: "human_review_only" | string;
  }>;
}

export type TenantRole = "owner" | "operator" | "viewer";
export type TenantMembershipStatus = "invited" | "active" | "revoked";

export type TelephonyRoutingMode = "exact_did";
export type TelephonyProvider = "connect" | "twilio" | "telnyx";
export type CallerVerificationMode = "standard" | "enhanced";
export type TelephonyLanguage = "tenant_default" | "en" | "hi";

export interface TelephonyPhoneNumber {
  phone_number: string;
  tenant_id: string;
  label: string;
  provider: TelephonyProvider;
  verification_mode: CallerVerificationMode;
  route_language: TelephonyLanguage;
  active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface VerificationContact {
  supplier_id: string;
  name: string;
  phone_masked: string;
  pin_configured: boolean;
  pin_updated_at: string | null;
  requires_rotation: boolean;
  locked: boolean;
}

export interface TelephonySettings {
  tenant_id: string;
  routing_mode: TelephonyRoutingMode;
  phone_numbers: TelephonyPhoneNumber[];
  verification_contacts: VerificationContact[];
}

export interface TelephonyPhoneNumberInput {
  phone_number: string;
  label: string;
  provider: TelephonyProvider;
  verification_mode: CallerVerificationMode;
  route_language: TelephonyLanguage;
  active: boolean;
}

export interface CallerVerificationPinInput {
  pin: string;
  confirm_pin: string;
}

export type VoicePersona = "professional" | "friendly" | "concise" | "assertive";
export type FallbackEscalationMode = "human_callback" | "transfer" | "voicemail";

export interface AgentSettings {
  tenant_id: string;
  name: string;
  agent_name: string;
  voice_persona: VoicePersona;
  default_language: "en" | "hi";
  welcome_message: string | null;
  system_prompt_override: string | null;
  business_hours_enabled: boolean;
  business_hours_start: string;
  business_hours_end: string;
  business_hours_timezone: string;
  business_days: string;
  out_of_hours_message: string | null;
  fallback_escalation_mode: FallbackEscalationMode;
  fallback_phone: string | null;
  fallback_email: string | null;
  max_verification_failures: number;
}

export interface AgentSettingsUpdateInput {
  agent_name?: string;
  voice_persona?: VoicePersona;
  default_language?: "en" | "hi";
  welcome_message?: string | null;
  system_prompt_override?: string | null;
  business_hours_enabled?: boolean;
  business_hours_start?: string;
  business_hours_end?: string;
  business_hours_timezone?: string;
  business_days?: string;
  out_of_hours_message?: string | null;
  fallback_escalation_mode?: FallbackEscalationMode;
  fallback_phone?: string | null;
  fallback_email?: string | null;
  max_verification_failures?: number;
}

export interface TenantMembership {
  id: string;
  tenant_id: string;
  user_id: string | null;
  role: TenantRole;
  status: TenantMembershipStatus;
  invited_by?: string;
  activated_at?: string | null;
  revoked_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  tenant?: {
    id: string;
    name: string;
    logo_url?: string | null;
    agent_name?: string | null;
    plan?: string | null;
  };
}

export interface TenantMembershipsResponse {
  memberships: TenantMembership[];
  demo_mode: boolean;
}

export type PrivacyRequestType = "access_export" | "deletion" | "demo_reset";
export type PrivacyRequestStatus = "pending_human_review" | "human_verification_required" | "approved_for_manual_export" | "blocked" | "cancelled";

export interface PrivacyPolicy {
  tenant_id: string;
  call_transcript_retention_days: number;
  communication_retention_days: number;
  recording_retention_days: number;
  recording_retrieval_enabled: false;
  updated_at: string | null;
}

export interface PrivacyRequest {
  id: string;
  tenant_id: string;
  request_type: PrivacyRequestType;
  status: PrivacyRequestStatus;
  requested_by: string;
  review_note: string;
  created_at: string | null;
  reviewed_at: string | null;
  reviewed_by: string | null;
}

export interface PrivacyOverview {
  tenant_id: string;
  policy: PrivacyPolicy;
  preview: {
    call_records_scanned: number;
    transcript_records_eligible_for_review: number;
    communication_records_scanned: number;
    communication_records_eligible_for_review: number;
    recording_reference_count: number;
    recording_retrieval_enabled: false;
  };
  execution: {
    mode: "preview_only";
    purge_job_enqueued: false;
    provider_accessed: false;
    raw_record_exported: false;
  };
  required_gate: string;
}

export interface DemoResetPreview {
  tenant_id: string;
  operation: "sanitized_demo_reset";
  execution: "blocked_preview_only";
  eligible_for_request: boolean;
  all_gates_met: boolean;
  gates: Array<{ code: string; met: boolean; detail: string }>;
  provider_accessed: false;
  data_deleted: false;
}

export interface DesignPartnerReadiness {
  tenant_id: string;
  status: "blocked" | "attention" | "ready_for_human_review";
  summary: {
    active_membership_count: number;
    active_owner_count: number;
    reliability_status: string;
    pilot_admission_status: string;
    campaign_worker_enabled: boolean;
    side_effect_worker_enabled: boolean;
    provider_activity_enabled: false;
  };
  gates: Array<{ code: string; category: string; status: "ready" | "attention" | "blocked"; owner: string; detail: string }>;
  automatic_activation: false;
  next_step: string;
}

// Day 49: Voice Eval Harness & Release Thresholds Scorecard types
export interface EvalTurnResult {
  user_text: string;
  reply_text: string;
  tool_calls: string[];
  word_count: number;
  latency_ms: number;
  passed: boolean;
  violations: string[];
}

export interface EvalScenarioResult {
  scenario_id: string;
  category: string;
  name: string;
  description: string;
  passed: boolean;
  hard_gate: boolean;
  hard_gate_violation: boolean;
  turns: EvalTurnResult[];
  total_latency_ms: number;
  avg_words: number;
  violations: string[];
}

export interface EvalCategoryScore {
  category: string;
  total: number;
  passed: number;
  failed: number;
  pass_rate: number;
  hard_gate_failures: number;
}

export interface EvalThreshold {
  name: string;
  target: number;
  actual: number;
  comparator: string;
  passed: boolean;
  is_hard_gate?: boolean;
}

export interface EvalReport {
  run_id: string;
  timestamp: string;
  tenant_id: string | null;
  total_scenarios: number;
  passed_scenarios: number;
  failed_scenarios: number;
  overall_pass_rate: number;
  security_pass_rate: number;
  verification_accuracy: number;
  tool_accuracy: number;
  avg_brevity_words: number;
  p95_latency_ms: number;
  hard_gate_passed: boolean;
  release_ready: boolean;
  thresholds: EvalThreshold[];
  category_scores: EvalCategoryScore[];
  scenarios: EvalScenarioResult[];
}

export interface EvalScenarioSummary {
  id: string;
  category: string;
  name: string;
  description: string;
  tenant_id: string;
  turns_count: number;
  hard_gate: boolean;
  must_call_tools: string[];
  forbidden_tools: string[];
  verified: boolean;
}

export interface TenantGoogleSheetsConfig {
  ok: boolean;
  tenant_id: string;
  is_connected: boolean;
  google_sheet_id: string;
  google_sheet_name: string | null;
  google_sheet_tab: string;
  google_sheet_email_tab: string;
  google_sheet_status: "connected" | "disconnected" | "error";
  google_sheet_connected_at: string | null;
  service_account_email: string;
  spreadsheet_url: string | null;
  global_fallback_configured: boolean;
  service_account_configured: boolean;
}

export interface ConnectGoogleSheetPayload {
  sheet_url_or_id: string;
  sheet_name?: string;
  call_tab?: string;
  email_tab?: string;
  auto_create_headers?: boolean;
}

export interface GoogleSheetsTestResult {
  ok: boolean;
  message?: string;
  error?: string;
  detail?: string;
  latency_ms?: number;
  sheet_id?: string;
  title?: string;
  tabs?: string[];
  configured_call_tab?: string;
  configured_email_tab?: string;
}

