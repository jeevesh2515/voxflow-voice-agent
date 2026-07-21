// Lightweight API client with multi-tenant filtering.

const API = process.env.NEXT_PUBLIC_API_URL || "";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const url = path.startsWith("http") ? path : `${API}${path}`;
  const r = await fetch(url, { cache: "no-store", ...init });
  if (!r.ok) {
    const body = await r.text();
    throw new Error(`${r.status} ${r.statusText}: ${body}`);
  }
  return r.json();
}

export const api = {
  tenants: () => http<any[]>("/api/tenants"),
  summary: (tenant_id?: string) => http<any>(`/api/summary${tenant_id ? `?tenant_id=${tenant_id}` : ""}`),
  suppliers: (q?: string, tenant_id?: string) => {
    const qs = new URLSearchParams();
    if (q) qs.set("q", q);
    if (tenant_id) qs.set("tenant_id", tenant_id);
    return http<any[]>(`/api/suppliers${qs.size ? `?${qs}` : ""}`);
  },
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
  shipments: (order_id?: string, tenant_id?: string) => {
    const qs = new URLSearchParams();
    if (order_id) qs.set("order_id", order_id);
    if (tenant_id) qs.set("tenant_id", tenant_id);
    return http<any[]>(`/api/shipments${qs.size ? `?${qs}` : ""}`);
  },
  calls: (limit = 50, tenant_id?: string) => {
    const qs = new URLSearchParams({ limit: String(limit) });
    if (tenant_id) qs.set("tenant_id", tenant_id);
    return http<any[]>(`/api/calls?${qs}`);
  },
  call: (id: string) => http<any>(`/api/calls/${id}`),
  appointments: (tenant_id?: string) =>
    http<any[]>(`/api/appointments${tenant_id ? `?tenant_id=${tenant_id}` : ""}`),
  communications: (tenant_id?: string) =>
    http<any[]>(`/api/communications${tenant_id ? `?tenant_id=${tenant_id}` : ""}`),
  health: () => http<any>("/api/health"),
};
