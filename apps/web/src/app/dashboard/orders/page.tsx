"use client";

import useSWR from "swr";
import Topbar from "@/components/Topbar";
import { api } from "@/lib/api";
import { fmtRelative, statusBg, statusColor } from "@/lib/format";
import { Package } from "lucide-react";
import { useTenant } from "@/lib/tenant-context";
import type { Order, OrderItem } from "@/lib/types";

export default function OrdersPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: orders, error, isLoading } = useSWR(["orders", activeTenantId], () =>
    api.orders({ tenant_id: activeTenantId }),
  );

  return (
    <>
      <Topbar title="Purchase Orders" subtitle={`${activeTenant.name} · ${orders?.length ?? 0} total`} />
      <div className="p-6">
        {isLoading && <div className="text-center text-ink-400 py-12 text-sm">Loading orders...</div>}
        {error && <div className="rounded border border-danger-500/30 bg-danger-500/10 p-3 text-sm text-danger-400">Failed to load orders. Is the API running?</div>}
        <div className="rounded-lg border border-ink-700/60 bg-ink-900/40 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-ink-900/60 text-[10px] font-mono uppercase tracking-wider text-ink-400">
              <tr>
                <th className="text-left px-4 py-3">Order ID</th>
                <th className="text-left px-4 py-3">Supplier</th>
                <th className="text-left px-4 py-3">Items</th>
                <th className="text-right px-4 py-3">Qty</th>
                <th className="text-left px-4 py-3">Status</th>
                <th className="text-right px-4 py-3">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-800/60">
              {(orders as Order[])?.map((o) => (
                <tr key={o.id} className="hover:bg-ink-800/30">
                  <td className="px-4 py-3 font-mono text-vox-300">{o.id}</td>
                  <td className="px-4 py-3 text-ink-100">{o.supplier_id}</td>
                  <td className="px-4 py-3 text-ink-300 font-mono text-xs">
                    {(o.items as OrderItem[]).map((i) => `${i.sku}×${i.quantity}`).join(", ")}
                  </td>
                  <td className="px-4 py-3 text-right text-ink-100">{o.total_qty}</td>
                  <td className="px-4 py-3">
                    <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${statusBg(o.status)} ${statusColor(o.status)}`}>
                      {o.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right text-ink-400 text-xs">{fmtRelative(o.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!isLoading && !error && (!orders || orders.length === 0) && (
            <div className="px-4 py-12 text-center">
              <Package className="mx-auto mb-3 text-ink-600" />
              <div className="text-sm text-ink-300">No orders logged for {activeTenant.name}.</div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
