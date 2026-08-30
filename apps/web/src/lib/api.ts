// Lightweight API client with multi-tenant filtering and auth.

import type {
  AnalyticsOverview,
  DrillResultsResponse,
  PilotOperations,
  PilotReadiness,
  RecoveryPreview,
  ReliabilityScorecard,
  TenantMembership,
  TenantMembershipsResponse,
  TenantRole,
  DemoResetPreview,
  PrivacyOverview,
  PrivacyPolicy,
  PrivacyRequest,
  PrivacyRequestStatus,
  PrivacyRequestType,
  DesignPartnerReadiness,
  CallerVerificationPinInput,
  TelephonyPhoneNumberInput,
  TelephonySettings,
  AgentSettings,
  AgentSettingsUpdateInput,
  Call,
  EscalationMetrics,
  EscalationsListResponse,
  EvalReport,
  EvalScenarioSummary,
  TenantGoogleSheetsConfig,
  ConnectGoogleSheetPayload,
  GoogleSheetsTestResult,
} from "./types";

const LOCAL_API_URL = "http://localhost:8000";
const PRODUCTION_API_URL = "https://voxflow-voice-agent.onrender.com";

function normalizeApiUrl(value: string): string {
  return value.replace(/\/+$/, "");
}

function getApiUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (configured) return normalizeApiUrl(configured);

  if (
    typeof window !== "undefined" &&
    (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
  ) {
    return LOCAL_API_URL;
  }

  // Explicit deployment configuration always takes precedence over this safe,
  // request-driven Render Free fallback.
  return PRODUCTION_API_URL;
}

function getAuthHeader(): Record<string, string> {
  if (typeof window === "undefined") return {};
  try {
    // A user explicitly selecting the quick demo must not inherit an unrelated
    // stale Supabase token from the same browser. The demo marker always maps
    // to the fixed read-only tenant and is checked first by the backend.
    const demoRaw = localStorage.getItem("voxflow_demo_user");
    if (demoRaw) {
      const demo = JSON.parse(demoRaw);
      return {
        "X-VoxFlow-Demo": "enabled",
        "X-VoxFlow-Demo-Tenant": String(demo?.tenant_id || "varun"),
      };
    }

    // Check custom voxflow_session.
    const raw = localStorage.getItem("voxflow_session");
    if (raw) {
      const session = JSON.parse(raw);
      const headers: Record<string, string> = {};
      const userId = session?.user?.id || session?.userId;
      if (session?.token) {
        headers["Authorization"] = `Bearer ${session.token}`;
      } else if (userId) {
        headers["Authorization"] = `Bearer ${userId}`;
      }
      if (userId) {
        headers["X-VoxFlow-User-Id"] = String(userId);
      }
      if (Object.keys(headers).length > 0) return headers;
    }


    // Check Supabase Auth session token (sb-*-auth-token).
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && (key.startsWith("sb-") && key.endsWith("-auth-token"))) {
        const item = localStorage.getItem(key);
        if (item) {
          const parsed = JSON.parse(item);
          const token = parsed?.access_token || parsed?.token;
          if (token) return { Authorization: `Bearer ${token}` };
        }
      }
    }
  } catch {
    // ignore parse errors
  }
  return {};
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const base = getApiUrl();
  const url = path.startsWith("http") ? path : `${base}${path}`;
  const headers = {
    "Content-Type": "application/json",
    ...getAuthHeader(),
    ...(init?.headers || {}),
  };
  try {
    const r = await fetch(url, { cache: "no-store", ...init, headers });
    if (!r.ok) {
      const body = await r.text();
      throw new Error(`${r.status} ${r.statusText}: ${body}`);
    }
    if (r.status === 204) return undefined as T;
    const body = await r.text();
    if (!body) return undefined as T;
    return JSON.parse(body) as T;
  } catch (err) {
    // Graceful fallback for empty/cold-start state
    if (path.includes("/api/calls") || path.includes("/api/active-calls")) {
      return [] as unknown as T;
    }
    throw err;
  }
}

async function downloadAnalyticsReport(tenantId: string, days: number): Promise<void> {
  const params = new URLSearchParams({ tenant_id: tenantId, days: String(days) });
  const response = await fetch(`${getApiUrl()}/api/analytics/report.csv?${params}`, {
    headers: getAuthHeader(),
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}: unable to export analytics report`);
  }

  const blob = await response.blob();
  const contentDisposition = response.headers.get("Content-Disposition") || "";
  const filenameMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filenameMatch?.[1] || "voxflow-enterprise-report.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

export const api = {
  tenants: () => http<any[]>("/api/tenants"),
  verifyTurnstile: (token: string, action: "sign_in" | "sign_up") =>
    http<{ ok: boolean; action: string; verification: "server_validated" }>("/api/auth/verify-turnstile", {
      method: "POST",
      body: JSON.stringify({ token, action }),
    }),
  myMemberships: () => http<TenantMembershipsResponse>("/api/tenants/memberships"),
  acceptMembership: (tenant_id: string) =>
    http<{ ok: boolean; created: boolean; membership: TenantMembership }>("/api/tenants/memberships/accept", {
      method: "POST",
      body: JSON.stringify({ tenant_id }),
    }),
  tenantMembers: (tenant_id: string) =>
    http<{ tenant_id: string; members: TenantMembership[] }>(`/api/tenants/${tenant_id}/members`),
  inviteTenantMember: (tenant_id: string, payload: { email: string; role: TenantRole; user_id?: string }) =>
    http<{ ok: boolean; created: boolean; delivery: string; membership: TenantMembership }>(`/api/tenants/${tenant_id}/members/invite`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  revokeTenantMember: (tenant_id: string, user_id: string) =>
    http<{ ok: boolean; membership: TenantMembership }>(`/api/tenants/${tenant_id}/members/${user_id}`, {
      method: "DELETE",
    }),
  updateTenantMemberRole: (tenant_id: string, user_id: string, role: TenantRole) =>
    http<{ ok: boolean; membership: TenantMembership }>(`/api/tenants/${tenant_id}/members/${user_id}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    }),
  privacyOverview: (tenant_id: string) => http<PrivacyOverview>(`/api/privacy/${tenant_id}/overview`),
  privacyPolicy: (tenant_id: string) => http<PrivacyPolicy>(`/api/privacy/${tenant_id}/policy`),
  updatePrivacyPolicy: (tenant_id: string, payload: Pick<PrivacyPolicy, "call_transcript_retention_days" | "communication_retention_days" | "recording_retention_days">) =>
    http<{ ok: boolean; policy: PrivacyPolicy; execution: string }>(`/api/privacy/${tenant_id}/policy`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  privacyRequests: (tenant_id: string) => http<{ tenant_id: string; requests: PrivacyRequest[] }>(`/api/privacy/${tenant_id}/requests`),
  createPrivacyRequest: (tenant_id: string, payload: { request_type: Extract<PrivacyRequestType, "access_export" | "deletion">; subject_reference: string }) =>
    http<{ ok: boolean; request: PrivacyRequest; execution: string }>(`/api/privacy/${tenant_id}/requests`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  reviewPrivacyRequest: (tenant_id: string, request_id: string, payload: { status: PrivacyRequestStatus; review_note: string }) =>
    http<{ ok: boolean; request: PrivacyRequest; execution: string }>(`/api/privacy/${tenant_id}/requests/${request_id}/review`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  designPartnerReadiness: (tenant_id: string) => http<DesignPartnerReadiness>(`/api/design-partner/${tenant_id}/readiness`),
  demoResetPreview: (tenant_id: string) => http<DemoResetPreview>(`/api/privacy/${tenant_id}/demo-reset-preview`),
  createDemoResetRequest: (tenant_id: string) =>
    http<{ ok: boolean; request: PrivacyRequest; execution: string }>(`/api/privacy/${tenant_id}/demo-reset-requests`, {
      method: "POST",
    }),
  provisionWorkspace: (payload: {
    tenant_id: string;
    name: string;
    plan?: string;
    admin_name?: string;
    admin_email?: string;
    phone_number?: string;
    seed_starter_data?: boolean;
  }) =>
    http<any>("/api/workspaces/provision", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getTenant: (tenant_id: string) => http<any>(`/api/admin/tenants/${tenant_id}`),
  updateTenant: (tenant_id: string, payload: any) =>
    http<any>(`/api/admin/tenants/${tenant_id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  getUsage: (tenant_id: string) => http<any>(`/api/admin/tenants/${tenant_id}/usage`),
  analyticsOverview: (tenant_id: string, days: number = 30) =>
    http<AnalyticsOverview>(`/api/analytics/overview?tenant_id=${tenant_id}&days=${days}`),
  downloadAnalyticsReport,
  pilotReadiness: (tenant_id: string) => http<PilotReadiness>(`/api/pilot-readiness/${tenant_id}`),
  pilotOperationsPreflight: (tenant_id: string) => http<PilotOperations>(`/api/pilot-operations/${tenant_id}/preflight`),
  pilotOperationsHoldPoint: (tenant_id: string) => http<PilotOperations>(`/api/pilot-operations/${tenant_id}/hold-point`),
  reliabilitySLOs: (tenant_id: string) => http<ReliabilityScorecard>(`/api/reliability/${tenant_id}/slos`),
  reliabilityDrills: (tenant_id: string, limit: number = 10) =>
    http<DrillResultsResponse>(`/api/reliability/${tenant_id}/drills?limit=${limit}`),
  reliabilityRecoveryPreview: (tenant_id: string) =>
    http<RecoveryPreview>(`/api/reliability/${tenant_id}/recovery-preview`),
  mapPhone: (tenant_id: string, phone_number: string, label?: string) =>
    http<any>(`/api/admin/tenants/${tenant_id}/phone-numbers`, {
      method: "POST",
      body: JSON.stringify({ phone_number, label }),
    }),
  telephonySettings: (tenant_id: string) =>
    http<TelephonySettings>(`/api/tenants/${encodeURIComponent(tenant_id)}/telephony`),
  createPhoneNumber: (tenant_id: string, payload: TelephonyPhoneNumberInput) =>
    http<unknown>(`/api/tenants/${encodeURIComponent(tenant_id)}/phone-numbers`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updatePhoneNumber: (tenant_id: string, phone_number: string, payload: TelephonyPhoneNumberInput) =>
    http<unknown>(`/api/tenants/${encodeURIComponent(tenant_id)}/phone-numbers/${encodeURIComponent(phone_number)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  deactivatePhoneNumber: (tenant_id: string, phone_number: string) =>
    http<unknown>(`/api/tenants/${encodeURIComponent(tenant_id)}/phone-numbers/${encodeURIComponent(phone_number)}`, {
      method: "DELETE",
    }),
  setCallerVerificationPin: (tenant_id: string, supplier_id: string, payload: CallerVerificationPinInput) =>
    http<unknown>(`/api/tenants/${encodeURIComponent(tenant_id)}/caller-verification/${encodeURIComponent(supplier_id)}/pin`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  agentSettings: (tenant_id: string) =>
    http<AgentSettings>(`/api/tenants/${encodeURIComponent(tenant_id)}/agent-settings`),
  updateAgentSettings: (tenant_id: string, payload: AgentSettingsUpdateInput) =>
    http<AgentSettings>(`/api/tenants/${encodeURIComponent(tenant_id)}/agent-settings`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  summary: (tenant_id?: string) => http<any>(`/api/summary${tenant_id ? `?tenant_id=${tenant_id}` : ""}`),
  suppliers: (q?: string, tenant_id?: string) => {
    const qs = new URLSearchParams();
    if (q) qs.set("q", q);
    if (tenant_id) qs.set("tenant_id", tenant_id);
    return http<any[]>(`/api/suppliers${qs.size ? `?${qs}` : ""}`);
  },
  createSupplier: (payload: { name: string; phone: string; city?: string; state?: string; pincode?: string; contact_person?: string; gstin?: string; auth_pin?: string }, tenant_id?: string) =>
    http<any>(`/api/suppliers${tenant_id ? `?tenant_id=${tenant_id}` : ""}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  stock: (params?: { sku?: string; warehouse?: string; tenant_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.sku) qs.set("sku", params.sku);
    if (params?.warehouse) qs.set("warehouse", params.warehouse);
    if (params?.tenant_id) qs.set("tenant_id", params.tenant_id);
    return http<any[]>(`/api/stock${qs.size ? `?${qs}` : ""}`);
  },

  orders: (params?: { supplier_id?: string; status?: string; tenant_id?: string }) => {
    const qs = new URLSearchParams();
    if (params?.supplier_id) qs.set("supplier_id", params.supplier_id);
    if (params?.status) qs.set("status", params.status);
    if (params?.tenant_id) qs.set("tenant_id", params.tenant_id);
    return http<any[]>(`/api/orders${qs.size ? `?${qs}` : ""}`);
  },
  createOrder: (payload: { supplier_id: string; items: { sku: string; quantity: number }[]; notes?: string }, tenant_id?: string) =>
    http<any>(`/api/orders${tenant_id ? `?tenant_id=${tenant_id}` : ""}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  shipments: (order_id?: string, tenant_id?: string) => {
    const qs = new URLSearchParams();
    if (order_id) qs.set("order_id", order_id);
    if (tenant_id) qs.set("tenant_id", tenant_id);
    return http<any[]>(`/api/shipments${qs.size ? `?${qs}` : ""}`);
  },

  calls: (limit = 50, tenant_id?: string, escalated?: boolean, resolution_status?: string) => {
    const qs = new URLSearchParams({ limit: String(limit) });
    if (tenant_id) qs.set("tenant_id", tenant_id);
    if (escalated !== undefined) qs.set("escalated", String(escalated));
    if (resolution_status !== undefined) qs.set("resolution_status", resolution_status);
    return http<any[]>(`/api/calls?${qs}`);
  },
  escalations: (tenant_id?: string) => {
    const qs = new URLSearchParams({ limit: "200" });
    if (tenant_id) qs.set("tenant_id", tenant_id);
    return http<any[]>(`/api/calls?${qs}`);
  },
  getEscalations: (
    tenant_id: string,
    params?: {
      status?: string;
      priority?: string;
      breached_only?: boolean;
      search?: string;
      limit?: number;
      offset?: number;
    }
  ) => {
    const qs = new URLSearchParams();
    if (params?.status && params.status !== "all") qs.set("status", params.status);
    if (params?.priority && params.priority !== "all") qs.set("priority", params.priority);
    if (params?.breached_only) qs.set("breached_only", "true");
    if (params?.search) qs.set("search", params.search);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    return http<EscalationsListResponse>(
      `/api/tenants/${encodeURIComponent(tenant_id)}/escalations${qs.size ? `?${qs}` : ""}`
    );
  },
  getEscalationMetrics: (tenant_id: string) =>
    http<EscalationMetrics>(`/api/tenants/${encodeURIComponent(tenant_id)}/escalations/metrics`),
  getEscalationDetail: (tenant_id: string, call_id: string) =>
    http<Call>(`/api/tenants/${encodeURIComponent(tenant_id)}/escalations/${encodeURIComponent(call_id)}`),
  assignEscalation: (tenant_id: string, call_id: string, assigned_to_user_id: string | null) =>
    http<Call>(
      `/api/tenants/${encodeURIComponent(tenant_id)}/escalations/${encodeURIComponent(call_id)}/assign`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ assigned_to_user_id }),
      }
    ),
  resolveEscalation: (
    tenant_id: string,
    call_id: string,
    payload: {
      status?: string;
      resolution_category?: string;
      staff_resolution: string;
    }
  ) =>
    http<Call>(
      `/api/tenants/${encodeURIComponent(tenant_id)}/escalations/${encodeURIComponent(call_id)}/resolve`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status: payload.status || "resolved",
          resolution_category: payload.resolution_category || "callback_completed",
          staff_resolution: payload.staff_resolution,
        }),
      }
    ),
  call: (id: string) => http<any>(`/api/calls/${id}`),
  patchResolution: (call_id: string, staff_resolution: string) =>
    http<any>(`/api/calls/${call_id}/resolution`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ staff_resolution }),
    }),
  activeCalls: (tenant_id?: string) =>
    http<any[]>(`/api/active-calls${tenant_id ? `?tenant_id=${tenant_id}` : ""}`),

  appointments: (tenant_id?: string) =>
    http<any[]>(`/api/appointments${tenant_id ? `?tenant_id=${tenant_id}` : ""}`),
  createAppointment: (payload: { supplier_id?: string; datetime: string; purpose?: string }, tenant_id?: string) =>
    http<any>(`/api/appointments${tenant_id ? `?tenant_id=${tenant_id}` : ""}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  communications: (tenant_id?: string) =>
    http<any[]>(`/api/communications${tenant_id ? `?tenant_id=${tenant_id}` : ""}`),
  createCommunication: (payload: { channel: string; recipient: string; subject?: string; body: string }, tenant_id?: string) =>
    http<any>(`/api/communications${tenant_id ? `?tenant_id=${tenant_id}` : ""}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  runEmailSummarizer: (tenant_id?: string, limit: number = 15) =>
    http<any>(`/api/admin/email-summarizer/run?tenant_id=${tenant_id || "varun"}&limit=${limit}`, {
      method: "POST",
    }),
  getEmailSummarizerStatus: (tenant_id?: string) =>
    http<any>(`/api/admin/email-summarizer/status?tenant_id=${tenant_id || "varun"}`),

  // Day 24: Outbound Voice Campaigns
  campaigns: (tenant_id?: string) =>
    http<any[]>(`/api/campaigns${tenant_id ? `?tenant_id=${tenant_id}` : ""}`),
  getCampaign: (id: string, tenant_id?: string) =>
    http<any>(`/api/campaigns/${id}?tenant_id=${tenant_id || "varun"}`),
  createCampaign: (
    payload: {
      name: string;
      campaign_type: string;
      targets: Array<{ phone: string; name?: string; context?: Record<string, any> }>;
      auto_start?: boolean;
    },
    tenant_id?: string,
  ) =>
    http<any>(`/api/campaigns${tenant_id ? `?tenant_id=${tenant_id}` : ""}`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  runCampaign: (id: string, max_concurrent: number = 5, tenant_id?: string) =>
    http<any>(`/api/campaigns/${id}/run?max_concurrent=${max_concurrent}&tenant_id=${tenant_id || "varun"}`, {
      method: "POST",
    }),
  getCampaignQueue: (id: string, tenant_id?: string) =>
    http<any[]>(`/api/campaigns/${id}/queue?tenant_id=${tenant_id || "varun"}`),
  campaignPolicyDecisions: (id: string, tenant_id?: string, limit: number = 50) =>
    http<any[]>(`/api/campaigns/${id}/policy-decisions?tenant_id=${tenant_id || "varun"}&limit=${limit}`),
  jobHealth: (tenant_id?: string) =>
    http<any>(`/api/jobs/health?tenant_id=${tenant_id || "varun"}`),
  // Day 44: Self-Serve SaaS Signup & Tenant Provisioning
  signupTenant: (payload: {
    company_name: string;
    email: string;
    name?: string;
    user_id?: string;
    tenant_id?: string;
    phone_number?: string;
    agent_name?: string;
    default_language?: "en" | "hi";
    plan?: "starter" | "pro" | "enterprise";
    seed_starter_data?: boolean;
    turnstile_token?: string | null;
  }) =>
    http<{
      ok: boolean;
      tenant_id: string;
      name: string;
      agent_name: string;
      default_language: string;
      plan: string;
      owner_user_id: string;
      owner_membership_created: boolean;
      phone_number?: string;
      starter_data_seeded?: boolean;
      stats?: Record<string, number>;
    }>("/api/auth/signup", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Day 45: Company Data Ingestion (CSV Bulk Import & CRUD)
  getImportEntities: () =>
    http<{
      entities: Array<{
        id: string;
        description: string;
        required_columns: string[];
        optional_columns: string[];
        sample_rows?: Array<Record<string, string>>;
      }>;
    }>("/api/data/entities"),

  getCsvTemplateUrl: (entity: string) => {
    const base = getApiUrl();
    return `${base}/api/data/templates/${encodeURIComponent(entity)}`;
  },

  validateCsvImport: (entity: string, csv_text: string, tenant_id?: string) =>
    http<{
      entity: string;
      total_rows: number;
      valid_rows: number;
      error_count: number;
      errors: Array<{ row_number: number; column: string; message: string; raw_value?: string }>;
      preview: Array<Record<string, any>>;
      headers: string[];
      is_valid: boolean;
    }>(`/api/data/${entity}/validate${tenant_id ? `?tenant_id=${tenant_id}` : ""}`, {
      method: "POST",
      body: JSON.stringify({ csv_text, tenant_id }),
    }),

  importCsvText: (
    entity: string,
    csv_text: string,
    mode: "upsert" | "strict" = "upsert",
    tenant_id?: string,
  ) =>
    http<{
      success: boolean;
      entity: string;
      tenant_id: string;
      inserted: number;
      updated: number;
      total_processed: number;
      message: string;
      errors: Array<{ row_number: number; column: string; message: string; raw_value?: string }>;
    }>(`/api/data/${entity}/import${tenant_id ? `?tenant_id=${tenant_id}` : ""}`, {
      method: "POST",
      body: JSON.stringify({ csv_text, mode }),
    }),

  importCsvFile: async (
    entity: string,
    file: File,
    mode: "upsert" | "strict" = "upsert",
    tenant_id?: string,
  ) => {
    const base = getApiUrl();
    const url = `${base}/api/data/${entity}/import${tenant_id ? `?tenant_id=${tenant_id}` : ""}`;
    const formData = new FormData();
    formData.append("file", file);
    formData.append("mode", mode);
    const authHeaders = getAuthHeader();
    const res = await fetch(url, {
      method: "POST",
      body: formData,
      headers: {
        ...authHeaders,
      },
    });
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`${res.status}: ${errText}`);
    }
    return res.json();
  },

  health: () => http<any>("/api/health"),

  // Day 49: Voice Eval Harness & Release Thresholds APIs
  evals: {
    getScorecard: () => http<EvalReport>("/api/evals/scorecard"),
    getTenantScorecard: (tenant_id: string) =>
      http<EvalReport>(`/api/tenants/${tenant_id}/evals/scorecard`),
    listScenarios: (category?: string, tenant_id?: string) => {
      const params = new URLSearchParams();
      if (category) params.set("category", category);
      if (tenant_id) params.set("tenant_id", tenant_id);
      const qs = params.toString();
      return http<EvalScenarioSummary[]>(`/api/evals/scenarios${qs ? `?${qs}` : ""}`);
    },
    runEval: (params: {
      category_filter?: string;
      tenant_id?: string;
      scenario_ids?: string[];
      min_overall_pass_rate?: number;
      min_security_pass_rate?: number;
    } = {}) =>
      http<EvalReport>("/api/evals/run", {
        method: "POST",
        body: JSON.stringify(params),
      }),
  },

  // Google Sheets Workspace Integrations
  googleSheets: {
    getConfig: (tenant_id: string) =>
      http<TenantGoogleSheetsConfig>(`/api/tenants/${encodeURIComponent(tenant_id)}/integrations/google-sheets`),
    connect: (tenant_id: string, payload: ConnectGoogleSheetPayload) =>
      http<{ ok: boolean; message: string; google_sheet_id: string; google_sheet_name: string; spreadsheet_url?: string }>(
        `/api/tenants/${encodeURIComponent(tenant_id)}/integrations/google-sheets/connect`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        }
      ),
    test: (tenant_id: string) =>
      http<GoogleSheetsTestResult>(
        `/api/tenants/${encodeURIComponent(tenant_id)}/integrations/google-sheets/test`,
        { method: "POST" }
      ),
    disconnect: (tenant_id: string) =>
      http<{ ok: boolean; message: string }>(
        `/api/tenants/${encodeURIComponent(tenant_id)}/integrations/google-sheets`,
        { method: "DELETE" }
      ),
  },
};

