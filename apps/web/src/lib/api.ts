// Lightweight API client with multi-tenant filtering and auth.

import type { AnalyticsOverview, PilotOperations, PilotReadiness } from "./types";

function getApiUrl(): string {
  if (typeof window !== "undefined") {
    if (window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
      return process.env.NEXT_PUBLIC_API_URL || "https://voxflow-voice-agent.onrender.com";
    }
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
}

const API = getApiUrl();

function getAuthHeader(): Record<string, string> {
  if (typeof window === "undefined") return {};
  try {
    // 1. Check custom voxflow_session
    const raw = localStorage.getItem("voxflow_session");
    if (raw) {
      const session = JSON.parse(raw);
      if (session?.token) {
        return { Authorization: `Bearer ${session.token}` };
      }
    }

    // 2. Check Supabase Auth session token (sb-*-auth-token)
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && (key.startsWith("sb-") && key.endsWith("-auth-token"))) {
        const item = localStorage.getItem(key);
        if (item) {
          const parsed = JSON.parse(item);
          const token = parsed?.access_token || parsed?.token;
          if (token) {
            return { Authorization: `Bearer ${token}` };
          }
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
    return r.json();
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
  mapPhone: (tenant_id: string, phone_number: string, label?: string) =>
    http<any>(`/api/admin/tenants/${tenant_id}/phone-numbers`, {
      method: "POST",
      body: JSON.stringify({ phone_number, label }),
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
  recentJobs: (tenant_id?: string, limit: number = 20) =>
    http<any[]>(`/api/jobs?tenant_id=${tenant_id || "varun"}&limit=${limit}`),

  health: () => http<any>("/api/health"),
};
