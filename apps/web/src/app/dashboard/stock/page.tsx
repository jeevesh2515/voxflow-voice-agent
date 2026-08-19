"use client";

import { useState, useMemo } from "react";
import useSWR from "swr";
import {
  Boxes,
  Search,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  Warehouse,
  IndianRupee,
  Layers,
  ArrowUpDown,
} from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";

export default function StockPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: stock, error, isLoading } = useSWR(["stock", activeTenantId], () =>
    api.stock({ tenant_id: activeTenantId }),
  );

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedWarehouse, setSelectedWarehouse] = useState("all");

  // Group by warehouse
  const warehouses = useMemo(() => {
    if (!stock) return [];
    const set = new Set((stock as any[]).map((s) => s.warehouse));
    return Array.from(set);
  }, [stock]);

  const filteredStock = useMemo(() => {
    if (!stock) return [];
    return (stock as any[]).filter((s) => {
      const matchSearch =
        s.sku.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.warehouse.toLowerCase().includes(searchQuery.toLowerCase());
      const matchWarehouse =
        selectedWarehouse === "all" || s.warehouse === selectedWarehouse;
      return matchSearch && matchWarehouse;
    });
  }, [stock, searchQuery, selectedWarehouse]);

  const stats = useMemo(() => {
    const list = (stock as any[]) || [];
    const totalUnits = list.reduce((sum, s) => sum + (s.quantity || 0), 0);
    const lowStockCount = list.filter((s) => s.quantity < 50).length;
    const totalValuation = list.reduce(
      (sum, s) => sum + (s.quantity || 0) * (s.mrp_inr || 0),
      0,
    );
    return {
      totalSkus: list.length,
      totalUnits,
      lowStockCount,
      totalValuation,
    };
  }, [stock]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* ==================== PAGE HEADER ==================== */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#12121e] p-6 rounded-2xl border border-[#242436] shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-mono text-[#94a3b8]">
            <span>Inventory</span>
            <span>/</span>
            <span className="text-[#00ffcc] font-bold">{activeTenant.name}</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-headline font-bold text-white tracking-tight">
            Stock & Warehouse Inventory
          </h1>
          <p className="text-xs sm:text-sm text-[#94a3b8]">
            Real-time warehouse SKU balance, batch depletion tracking, and automated re-order thresholds.
          </p>
        </div>
      </header>

      {/* ==================== STAT CARDS ==================== */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Total SKUs</span>
            <Layers size={16} className="text-amber-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-white">{stats.totalSkus}</div>
          <div className="text-xs text-[#94a3b8] mt-1">{warehouses.length} active hubs</div>
        </div>

        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Inventory Units</span>
            <Boxes size={16} className="text-[#00ffcc]" />
          </div>
          <div className="text-2xl font-headline font-bold text-[#00ffcc]">
            {stats.totalUnits.toLocaleString()}
          </div>
          <div className="text-xs text-[#94a3b8] mt-1">Available for dispatch</div>
        </div>

        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Low Stock Alerts</span>
            <AlertTriangle size={16} className="text-[#ff2d78]" />
          </div>
          <div className="text-2xl font-headline font-bold text-[#ff2d78]">{stats.lowStockCount}</div>
          <div className="text-xs text-[#ff2d78] mt-1">&lt; 50 units remaining</div>
        </div>

        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Total Valuation</span>
            <IndianRupee size={16} className="text-purple-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-purple-400">
            ₹{(stats.totalValuation / 100000).toFixed(2)}L
          </div>
          <div className="text-xs text-[#94a3b8] mt-1">Estimated MRP inventory</div>
        </div>
      </div>

      {/* ==================== WAREHOUSE TABS & SEARCH ==================== */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between bg-[#141422] p-3 rounded-2xl border border-[#28283c]">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#64748b]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search SKU code, product name, warehouse..."
            className="w-full bg-[#10101a] border border-[#28283c] rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder:text-[#64748b] focus:outline-none focus:border-[#ff2d78]"
          />
        </div>
        <div className="flex items-center bg-[#10101a] p-1 rounded-xl border border-[#28283c] overflow-x-auto">
          <button
            onClick={() => setSelectedWarehouse("all")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors shrink-0 ${
              selectedWarehouse === "all"
                ? "bg-[#ff2d78] text-white"
                : "text-[#94a3b8] hover:text-white"
            }`}
          >
            All Warehouses
          </button>
          {warehouses.map((wh) => (
            <button
              key={wh}
              onClick={() => setSelectedWarehouse(wh)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors shrink-0 ${
                selectedWarehouse === wh
                  ? "bg-[#ff2d78] text-white"
                  : "text-[#94a3b8] hover:text-white"
              }`}
            >
              {wh}
            </button>
          ))}
        </div>
      </div>

      {/* ==================== STOCK TABLE ==================== */}
      <div className="bg-[#141422] rounded-2xl border border-[#28283c] overflow-hidden shadow-sm">
        {isLoading && (
          <div className="py-16 text-center text-[#94a3b8] text-xs">
            Loading inventory registry...
          </div>
        )}

        {error && (
          <div className="p-6 text-center text-red-400 bg-red-500/10 text-xs">
            Failed to load stock data. Please verify backend API connectivity.
          </div>
        )}

        {!isLoading && !error && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#181828] border-b border-[#28283c] text-[11px] font-mono uppercase tracking-wider text-[#94a3b8]">
                <tr>
                  <th className="px-5 py-3.5">SKU Code</th>
                  <th className="px-5 py-3.5">Product Name</th>
                  <th className="px-5 py-3.5">Warehouse Hub</th>
                  <th className="px-5 py-3.5">Pack Size</th>
                  <th className="px-5 py-3.5 text-right">Unit MRP</th>
                  <th className="px-5 py-3.5 text-right">Quantity In Stock</th>
                  <th className="px-5 py-3.5 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#242436]">
                {filteredStock.map((s) => {
                  const isLow = s.quantity < 50;
                  const isModerate = s.quantity >= 50 && s.quantity < 100;
                  return (
                    <tr key={`${s.warehouse}-${s.sku}`} className="hover:bg-[#181828] transition-colors">
                      <td className="px-5 py-4 font-mono font-bold text-[#00ffcc]">
                        {s.sku}
                      </td>
                      <td className="px-5 py-4 text-white font-medium">
                        {s.name || s.sku}
                      </td>
                      <td className="px-5 py-4 text-[#94a3b8]">
                        <div className="flex items-center gap-1.5">
                          <Warehouse size={13} className="text-amber-400" />
                          <span>{s.warehouse}</span>
                        </div>
                      </td>
                      <td className="px-5 py-4 text-[#94a3b8] font-mono">{s.pack_size || "Standard"}</td>
                      <td className="px-5 py-4 text-right font-mono text-white">
                        ₹{s.mrp_inr?.toFixed(2) || "0.00"}
                      </td>
                      <td className="px-5 py-4 text-right font-bold">
                        <span
                          className={
                            isLow
                              ? "text-[#ff2d78]"
                              : isModerate
                              ? "text-amber-400"
                              : "text-[#00ffcc]"
                          }
                        >
                          {s.quantity.toLocaleString()}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-right">
                        <span
                          className={`text-[10px] font-mono font-bold uppercase px-2.5 py-0.5 rounded-md border ${
                            isLow
                              ? "bg-[#ff2d78]/15 text-[#ff2d78] border-[#ff2d78]/30"
                              : isModerate
                              ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
                              : "bg-[#00ffcc]/15 text-[#00ffcc] border-[#00ffcc]/30"
                          }`}
                        >
                          {isLow ? "Low Stock" : isModerate ? "Moderate" : "Healthy"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {filteredStock.length === 0 && (
              <div className="p-16 text-center space-y-3">
                <Boxes className="mx-auto text-[#64748b]" size={36} />
                <div className="text-sm text-white font-headline font-semibold">No SKUs found</div>
                <p className="text-xs text-[#94a3b8] max-w-sm mx-auto">
                  {searchQuery
                    ? `No products matching "${searchQuery}".`
                    : `Stock items will appear once initialized for ${activeTenant.name}.`}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
