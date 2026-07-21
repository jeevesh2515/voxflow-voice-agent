"use client";

import useSWR from "swr";
import Topbar from "@/components/Topbar";
import { api } from "@/lib/api";
import { fmtRelative, statusBg, statusColor } from "@/lib/format";
import { Truck } from "lucide-react";
import { useTenant } from "@/lib/tenant-context";

export default function ShipmentsPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: shipments } = useSWR(["shipments", activeTenantId], () =>
    api.shipments(undefined, activeTenantId),
  );

  return (
    <>
      <Topbar title="Shipment Tracking" subtitle={`${activeTenant.name} · ${shipments?.length ?? 0} active`} />
      <div className="p-6 space-y-3">
        {shipments?.map((s) => (
          <div key={s.id} className="rounded-lg border border-ink-700/60 bg-ink-900/40 p-4">
            <div className="flex items-center gap-3 mb-3">
              <Truck className="text-vox-400" size={18} />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-mono text-vox-300">{s.id}</div>
                <div className="text-[11px] font-mono text-ink-400">
                  {s.carrier} · tracking {s.tracking_no} · order {s.order_id}
                </div>
              </div>
              <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${statusBg(s.status)} ${statusColor(s.status)}`}>
                {s.status}
              </span>
            </div>
            {s.history && s.history.length > 0 && (
              <div className="border-l border-ink-700/60 pl-4 space-y-2">
                {s.history.map((h: any, i: number) => (
                  <div key={i} className="text-xs">
                    <div className={`font-mono uppercase tracking-wider ${statusColor(h.status)}`}>
                      {h.status}
                    </div>
                    <div className="text-ink-300">{h.note}</div>
                    <div className="text-ink-500 text-[10px] font-mono">{fmtRelative(h.at)}</div>
                  </div>
                ))}
              </div>
            )}
            {s.expected_delivery && (
              <div className="mt-2 text-[11px] text-ink-400">
                Expected delivery: <span className="text-ink-100">{new Date(s.expected_delivery).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })}</span>
              </div>
            )}
          </div>
        ))}
        {(!shipments || shipments.length === 0) && (
          <div className="rounded-lg border border-dashed border-ink-700/60 p-12 text-center">
            <Truck className="mx-auto mb-3 text-ink-600" />
            <div className="text-sm text-ink-300">No shipments found for {activeTenant.name}.</div>
          </div>
        )}
      </div>
    </>
  );
}
