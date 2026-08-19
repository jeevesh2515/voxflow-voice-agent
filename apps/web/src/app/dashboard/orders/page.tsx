"use client";

import { useState, useMemo } from "react";
import useSWR from "swr";
import { Package, Search, ChevronDown } from "lucide-react";
import { api } from "@/lib/api";
import { fmtRelative, statusBg, statusColor } from "@/lib/format";
import { useTenant } from "@/lib/tenant-context";
import type { Order, OrderItem } from "@/lib/types";
import SectionCard from "@/components/dashboard/SectionCard";
import DataTable from "@/components/dashboard/DataTable";

export default function OrdersPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: orders, error, isLoading } = useSWR(["orders", activeTenantId], () =>
    api.orders({ tenant_id: activeTenantId }),
  );

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const statuses = useMemo(() => {
    if (!orders) return [];
    return Array.from(new Set(orders.map((o) => o.status)));
  }, [orders]);

  const filteredOrders = useMemo(() => {
    if (!orders) return [];
    let result = orders;
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter((o) => o.id.toLowerCase().includes(q) || o.supplier_id.toLowerCase().includes(q));
    }
    if (statusFilter !== "all") {
      result = result.filter((o) => o.status === statusFilter);
    }
    return result.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [orders, search, statusFilter]);

  const columns = [
    {
      key: "id",
      label: "Order ID",
      render: (o: Order) => <span className="font-mono text-[#ff2d78] text-xs font-bold">{o.id}</span>,
    },
    {
      key: "supplier",
      label: "Supplier",
      render: (o: Order) => <span className="text-[#e8e0f0]">{o.supplier_id}</span>,
    },
    {
      key: "items",
      label: "Items",
      render: (o: Order) => (
        <span className="text-[#a098b0] text-xs font-mono">
          {(o.items as OrderItem[]).map((i) => `${i.sku}×${i.quantity}`).join(", ")}
        </span>
      ),
    },
    {
      key: "qty",
      label: "Qty",
      render: (o: Order) => <span className="text-[#e8e0f0] font-mono text-xs text-right block">{o.total_qty}</span>,
      className: "text-right",
    },
    {
      key: "status",
      label: "Status",
      render: (o: Order) => (
        <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${statusBg(o.status)} ${statusColor(o.status)}`}>
          {o.status}
        </span>
      ),
    },
    {
      key: "created",
      label: "Created",
      render: (o: Order) => <span className="text-[#a098b0] text-xs font-mono">{fmtRelative(o.created_at)}</span>,
    },
  ];

  return (
    <div className="space-y-6">
      <SectionCard
        title="Purchase Orders"
        subtitle={`${activeTenant.name} · ${orders?.length ?? 0} total`}
        icon={<Package size={18} className="text-[#ff2d78]" />}
        action={
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#a098b0]" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search orders..."
                className="pl-9 pr-4 py-2 rounded-lg bg-[#0a0a12] border border-[#302840] text-xs text-[#e8e0f0] placeholder-[#5a5068] focus:outline-none focus:border-[#ff2d78]/50 w-48"
              />
            </div>
            <div className="relative">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="appearance-none bg-[#0a0a12] border border-[#302840] text-xs text-[#e8e0f0] rounded-lg px-3 py-2 pr-8 focus:outline-none focus:border-[#ff2d78]/50"
              >
                <option value="all">All Status</option>
                {statuses.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              <ChevronDown size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#a098b0] pointer-events-none" />
            </div>
          </div>
        }
      >
        {isLoading && <div className="text-center text-[#a098b0] py-12 text-sm">Loading orders...</div>}
        {error && <div className="rounded border border-danger-500/30 bg-danger-500/10 p-3 text-sm text-danger-500">Failed to load orders. Is the API running?</div>}
        {!isLoading && !error && (
          <DataTable
            columns={columns}
            data={filteredOrders}
            keyExtractor={(o) => o.id}
            loading={isLoading}
            emptyState={
              <div className="px-4 py-12 text-center">
                <Package size={32} className="mx-auto text-[#5a5068] mb-3" />
                <div className="text-sm text-[#a098b0]">No orders logged for {activeTenant.name}.</div>
              </div>
            }
          />
        )}
      </SectionCard>
    </div>
  );
}
