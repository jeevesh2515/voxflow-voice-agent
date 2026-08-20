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
  sheet_synced: boolean;
  verified: boolean;
  recording_url?: string | null;
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
