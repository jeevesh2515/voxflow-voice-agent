// Lightweight API client with multi-tenant filtering and auth.

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

export const api = {
  tenants: () => http<any[]>("/api/tenants"),
  getTenant: (tenant_id: string) => http<any>(`/api/admin/tenants/${tenant_id}`),
  updateTenant: (tenant_id: string, payload: any) =>
    http<any>(`/api/admin/tenants/${tenant_id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  getUsage: (tenant_id: string) => http<any>(`/api/admin/tenants/${tenant_id}/usage`),
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

  health: () => http<any>("/api/health"),
};
