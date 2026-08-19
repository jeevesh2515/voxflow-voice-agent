"use client";

import { useState, useMemo } from "react";
import useSWR from "swr";
import { Truck, Search } from "lucide-react";
import { api } from "@/lib/api";
import { fmtRelative, statusBg, statusColor } from "@/lib/format";
import { useTenant } from "@/lib/tenant-context";
import type { Shipment } from "@/lib/types";
import SectionCard from "@/components/dashboard/SectionCard";
import DataTable from "@/components/dashboard/DataTable";

export default function ShipmentsPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: shipments, error, isLoading } = useSWR(["shipments", activeTenantId], () =>
    api.shipments(undefined, activeTenantId),
  );

  const [search, setSearch] = useState("");

  const filteredShipments = useMemo(() => {
    if (!shipments) return [];
    if (!search.trim()) return shipments;
    const q = search.toLowerCase();
    return shipments.filter((s) =>
      s.id.toLowerCase().includes(q) ||
      s.carrier.toLowerCase().includes(q) ||
      s.tracking_no.toLowerCase().includes(q) ||
      s.order_id.toLowerCase().includes(q)
    );
  }, [shipments, search]);

  const columns = [
    {
      key: "id",
      label: "Shipment ID",
      render: (s: Shipment) => <span className="font-mono text-[#ff2d78] text-xs font-bold">{s.id}</span>,
    },
    {
      key: "carrier",
      label: "Carrier",
      render: (s: Shipment) => <span className="text-[#e8e0f0] text-xs">{s.carrier}</span>,
    },
    {
      key: "tracking",
      label: "Tracking",
      render: (s: Shipment) => <span className="font-mono text-[#a098b0] text-xs">{s.tracking_no}</span>,
    },
    {
      key: "order",
      label: "Order",
      render: (s: Shipment) => <span className="font-mono text-[#a098b0] text-xs">{s.order_id}</span>,
    },
    {
      key: "status",
      label: "Status",
      render: (s: Shipment) => (
        <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${statusBg(s.status)} ${statusColor(s.status)}`}>
          {s.status}
        </span>
      ),
    },
    {
      key: "expected",
      label: "Expected",
      render: (s: Shipment) => (
        <span className="text-[#a098b0] text-xs">
          {s.expected_delivery ? new Date(s.expected_delivery).toLocaleDateString("en-IN") : "—"}
        </span>
      ),
    },
    {
      key: "history",
      label: "Updates",
      render: (s: Shipment) => (
        <span className="text-[#a098b0] text-xs">{s.history?.length ?? 0} events</span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <SectionCard
        title="Shipment Tracking"
        subtitle={`${activeTenant.name} · ${shipments?.length ?? 0} active`}
        icon={<Truck size={18} className="text-[#00ffcc]" />}
        action={
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#a098b0]" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search shipments..."
              className="pl-9 pr-4 py-2 rounded-lg bg-[#0a0a12] border border-[#302840] text-xs text-[#e8e0f0] placeholder-[#5a5068] focus:outline-none focus:border-[#00ffcc]/50 w-48"
            />
          </div>
        }
      >
        {isLoading && <div className="text-center text-[#a098b0] py-12 text-sm">Loading shipments...</div>}
        {error && <div className="rounded border border-danger-500/30 bg-danger-500/10 p-3 text-sm text-danger-500">Failed to load shipments. Is the API running?</div>}
        {!isLoading && !error && (
          <DataTable
            columns={columns}
            data={filteredShipments}
            keyExtractor={(s) => s.id}
            loading={isLoading}
            emptyState={
              <div className="px-4 py-12 text-center">
                <Truck size={32} className="mx-auto text-[#5a5068] mb-3" />
                <div className="text-sm text-[#a098b0]">No shipments found for {activeTenant.name}.</div>
              </div>
            }
          />
        )}
      </SectionCard>
    </div>
  );
}
