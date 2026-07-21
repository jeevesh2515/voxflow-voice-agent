// Lightweight API client. Uses NEXT_PUBLIC_API_URL with rewrite fallback.

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
  summary: () => http<any>("/api/summary"),
  suppliers: (q?: string) => http<any[]>(`/api/suppliers${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  stock: (params?: { sku?: string; warehouse?: string }) => {
    const qs = new URLSearchParams();
    if (params?.sku) qs.set("sku", params.sku);
    if (params?.warehouse) qs.set("warehouse", params.warehouse);
    return http<any[]>(`/api/stock${qs.size ? `?${qs}` : ""}`);
  },
  orders: (params?: { supplier_id?: string; status?: string }) => {
    const qs = new URLSearchParams();
    if (params?.supplier_id) qs.set("supplier_id", params.supplier_id);
    if (params?.status) qs.set("status", params.status);
    return http<any[]>(`/api/orders${qs.size ? `?${qs}` : ""}`);
  },
  shipments: (order_id?: string) =>
    http<any[]>(`/api/shipments${order_id ? `?order_id=${order_id}` : ""}`),
  calls: (limit = 50) => http<any[]>(`/api/calls?limit=${limit}`),
  call: (id: string) => http<any>(`/api/calls/${id}`),
  health: () => http<any>("/api/health"),
};
