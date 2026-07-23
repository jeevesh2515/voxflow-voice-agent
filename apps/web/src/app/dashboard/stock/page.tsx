"use client";

import useSWR from "swr";
import Topbar from "@/components/Topbar";
import { api } from "@/lib/api";
import { Boxes } from "lucide-react";
import { useTenant } from "@/lib/tenant-context";

export default function StockPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: stock, error, isLoading } = useSWR(["stock", activeTenantId], () =>
    api.stock({ tenant_id: activeTenantId }),
  );

  // Group by warehouse
  const byWarehouse = (stock || []).reduce<Record<string, any[]>>((acc, s) => {
    (acc[s.warehouse] ||= []).push(s);
    return acc;
  }, {});

  return (
    <>
      <Topbar
        title="Stock & Inventory"
        subtitle={`${activeTenant.name} · ${stock?.length ?? 0} SKUs across ${Object.keys(byWarehouse).length} warehouses`}
      />
      <div className="p-6 space-y-4">
        {Object.entries(byWarehouse).map(([wh, items]) => (
          <div key={wh} className="rounded-lg border border-ink-700/60 bg-ink-900/40 overflow-hidden">
            <div className="px-5 py-3 border-b border-ink-700/60 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-ink-50">{wh}</h3>
              <span className="text-[10px] font-mono uppercase tracking-wider text-ink-400">
                {items.length} SKUs
              </span>
            </div>
            <table className="w-full text-sm">
              <thead className="bg-ink-900/60 text-[10px] font-mono uppercase tracking-wider text-ink-400">
                <tr>
                  <th className="text-left px-4 py-2">SKU</th>
                  <th className="text-left px-4 py-2">Product</th>
                  <th className="text-left px-4 py-2">Pack size</th>
                  <th className="text-right px-4 py-2">MRP</th>
                  <th className="text-right px-4 py-2">Quantity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-800/60">
                {items.map((s) => (
                  <tr key={`${s.warehouse}-${s.sku}`} className="hover:bg-ink-800/30">
                    <td className="px-4 py-2 font-mono text-vox-300">{s.sku}</td>
                    <td className="px-4 py-2 text-ink-100">{s.name}</td>
                    <td className="px-4 py-2 text-ink-300">{s.pack_size}</td>
                    <td className="px-4 py-2 text-right text-ink-300">₹{s.mrp_inr}</td>
                    <td className="px-4 py-2 text-right font-mono">
                      <span className={s.quantity < 50 ? "text-danger-500" : s.quantity < 100 ? "text-warn-500" : "text-success-500"}>
                        {s.quantity.toLocaleString()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
        {isLoading && <div className="text-center text-ink-400 py-12 text-sm">Loading stock data...</div>}
        {error && <div className="rounded border border-danger-500/30 bg-danger-500/10 p-3 text-sm text-danger-400">Failed to load stock. Is the API running?</div>}
        {!isLoading && !error && (!stock || stock.length === 0) && (
          <div className="rounded-lg border border-dashed border-ink-700/60 p-12 text-center">
            <Boxes className="mx-auto mb-3 text-ink-600" />
            <div className="text-sm text-ink-300">No stock data found for {activeTenant.name}.</div>
          </div>
        )}
      </div>
    </>
  );
}
