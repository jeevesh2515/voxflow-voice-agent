"use client";

import { useState, useMemo } from "react";
import useSWR from "swr";
import { Boxes, Search, ChevronDown } from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";
import SectionCard from "@/components/dashboard/SectionCard";
import DataTable from "@/components/dashboard/DataTable";

export default function StockPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: stock, error, isLoading } = useSWR(["stock", activeTenantId], () =>
    api.stock({ tenant_id: activeTenantId }),
  );

  const [search, setSearch] = useState("");
  const [warehouseFilter, setWarehouseFilter] = useState<string>("all");

  const warehouses = useMemo(() => {
    if (!stock) return [];
    return Array.from(new Set(stock.map((s) => s.warehouse)));
  }, [stock]);

  const filteredStock = useMemo(() => {
    if (!stock) return [];
    let result = stock;
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter((s) => s.sku.toLowerCase().includes(q) || s.name.toLowerCase().includes(q));
    }
    if (warehouseFilter !== "all") {
      result = result.filter((s) => s.warehouse === warehouseFilter);
    }
    return result;
  }, [stock, search, warehouseFilter]);

  const columns = [
    {
      key: "sku",
      label: "SKU",
      className: "font-mono text-vox-300 text-xs",
      render: (s: any) => <span className="font-mono text-[#ff2d78] text-xs">{s.sku}</span>,
    },
    {
      key: "name",
      label: "Product",
      render: (s: any) => <span className="text-[#e8e0f0]">{s.name}</span>,
    },
    {
      key: "warehouse",
      label: "Warehouse",
      render: (s: any) => (
        <span className="text-[10px] font-mono uppercase tracking-wider text-[#a098b0] px-2 py-0.5 rounded border border-[#302840]/40 bg-[#1e1e30]/30">
          {s.warehouse}
        </span>
      ),
    },
    {
      key: "pack",
      label: "Pack Size",
      render: (s: any) => <span className="text-[#a098b0] text-xs">{s.pack_size}</span>,
    },
    {
      key: "mrp",
      label: "MRP",
      render: (s: any) => <span className="text-[#e8e0f0] font-mono text-xs">₹{s.mrp_inr}</span>,
      className: "text-right",
    },
    {
      key: "qty",
      label: "Quantity",
      render: (s: any) => (
        <span className={`font-mono text-xs font-bold ${s.quantity < 50 ? "text-danger-500" : s.quantity < 100 ? "text-warn-500" : "text-success-500"}`}>
          {s.quantity.toLocaleString()}
        </span>
      ),
      className: "text-right",
    },
  ];

  return (
    <div className="space-y-6">
      <SectionCard
        title="Stock & Inventory"
        subtitle={`${activeTenant.name} · ${stock?.length ?? 0} SKUs`}
        icon={<Boxes size={18} className="text-[#00ffcc]" />}
        action={
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#a098b0]" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search SKU or product..."
                className="pl-9 pr-4 py-2 rounded-lg bg-[#0a0a12] border border-[#302840] text-xs text-[#e8e0f0] placeholder-[#5a5068] focus:outline-none focus:border-[#00ffcc]/50 w-48"
              />
            </div>
            <div className="relative">
              <select
                value={warehouseFilter}
                onChange={(e) => setWarehouseFilter(e.target.value)}
                className="appearance-none bg-[#0a0a12] border border-[#302840] text-xs text-[#e8e0f0] rounded-lg px-3 py-2 pr-8 focus:outline-none focus:border-[#00ffcc]/50"
              >
                <option value="all">All Warehouses</option>
                {warehouses.map((w) => (
                  <option key={w} value={w}>{w}</option>
                ))}
              </select>
              <ChevronDown size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#a098b0] pointer-events-none" />
            </div>
          </div>
        }
      >
        {isLoading && <div className="text-center text-[#a098b0] py-12 text-sm">Loading stock data...</div>}
        {error && <div className="rounded border border-danger-500/30 bg-danger-500/10 p-3 text-sm text-danger-500">Failed to load stock. Is the API running?</div>}
        {!isLoading && !error && (
          <DataTable
            columns={columns}
            data={filteredStock}
            keyExtractor={(s) => `${s.warehouse}-${s.sku}`}
            loading={isLoading}
            emptyState={
              <div className="px-4 py-12 text-center">
                <Boxes size={32} className="mx-auto text-[#5a5068] mb-3" />
                <div className="text-sm text-[#a098b0]">No stock data found for {activeTenant.name}.</div>
              </div>
            }
          />
        )}
      </SectionCard>
    </div>
  );
}
