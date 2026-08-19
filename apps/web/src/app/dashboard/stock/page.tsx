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
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-label uppercase tracking-widest text-[#a098b0] mb-1">
            <span>Inventory</span>
            <span>/</span>
            <span className="text-[#00ffcc] font-bold">{activeTenant.name}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-headline font-extrabold text-[#e8e0f0] tracking-[0.05em] uppercase">
            Stock & <span className="text-[#ffe04a] text-glow-accent">Inventory</span>
          </h1>
          <p className="text-[#a098b0] font-body text-sm mt-1">
            Real-time warehouse SKU balance, batch depletion tracking, and automated re-order thresholds.
          </p>
        </div>
      </header>

      {/* ==================== STAT CARDS ==================== */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-4 rounded-2xl border border-[#ffe04a]/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>Total SKUs</span>
            <Layers size={16} className="text-[#ffe04a]" />
          </div>
          <div className="text-2xl font-headline font-bold text-[#e8e0f0]">{stats.totalSkus}</div>
          <div className="text-[10px] text-[#a098b0] mt-1">{warehouses.length} active hubs</div>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-[#00ffcc]/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>Inventory Units</span>
            <Boxes size={16} className="text-[#00ffcc]" />
          </div>
          <div className="text-2xl font-headline font-bold text-[#00ffcc]">
            {stats.totalUnits.toLocaleString()}
          </div>
          <div className="text-[10px] text-[#00ffcc] mt-1">Ready for dispatch</div>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-[#ff2d78]/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>Low Stock Alerts</span>
            <AlertTriangle size={16} className="text-[#ff2d78]" />
          </div>
          <div className="text-2xl font-headline font-bold text-[#ff2d78]">{stats.lowStockCount}</div>
          <div className="text-[10px] text-[#ff2d78] mt-1">&lt; 50 units remaining</div>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-purple-500/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>Total Valuation</span>
            <IndianRupee size={16} className="text-purple-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-purple-400">
            ₹{(stats.totalValuation / 100000).toFixed(2)}L
          </div>
          <div className="text-[10px] text-[#a098b0] mt-1">At standard MRP</div>
        </div>
      </div>

      {/* ==================== WAREHOUSE TABS & SEARCH ==================== */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between bg-[#111118]/80 p-3 rounded-2xl border border-[#302840]/60">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#a098b0]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search SKU code, product name, warehouse..."
            className="w-full bg-[#181824] border border-[#302840]/60 rounded-xl pl-9 pr-4 py-2 text-xs text-[#e8e0f0] placeholder:text-[#a098b0]/50 focus:outline-none focus:border-[#ffe04a] transition-all font-body"
          />
        </div>
        <div className="flex items-center gap-2 overflow-x-auto">
          <button
            onClick={() => setSelectedWarehouse("all")}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-label uppercase tracking-wider transition-all shrink-0 ${
              selectedWarehouse === "all"
                ? "bg-[#ffe04a] text-[#1a0010] font-bold shadow-[0_0_12px_rgba(255,224,74,0.4)]"
                : "bg-[#181824] text-[#a098b0] hover:text-[#e8e0f0] border border-[#302840]/60"
            }`}
          >
            All Warehouses
          </button>
          {warehouses.map((wh) => (
            <button
              key={wh}
              onClick={() => setSelectedWarehouse(wh)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-label uppercase tracking-wider transition-all shrink-0 ${
                selectedWarehouse === wh
                  ? "bg-[#ffe04a] text-[#1a0010] font-bold shadow-[0_0_12px_rgba(255,224,74,0.4)]"
                  : "bg-[#181824] text-[#a098b0] hover:text-[#e8e0f0] border border-[#302840]/60"
              }`}
            >
              {wh}
            </button>
          ))}
        </div>
      </div>

      {/* ==================== STOCK TABLE ==================== */}
      <div className="glass-panel rounded-2xl border border-[#302840]/60 overflow-hidden shadow-2xl">
        {isLoading && (
          <div className="py-16 text-center text-[#a098b0] text-xs font-label uppercase tracking-widest flex items-center justify-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#ffe04a] animate-ping" /> Loading inventory registry...
          </div>
        )}

        {error && (
          <div className="p-6 text-center text-[#ff2d78] bg-[#ff2d78]/5 text-xs font-body">
            Failed to load stock data. Please verify backend API connectivity.
          </div>
        )}

        {!isLoading && !error && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm font-body">
              <thead className="bg-[#181824]/90 border-b border-[#302840]/60 text-[10px] font-label uppercase tracking-wider text-[#a098b0]">
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
              <tbody className="divide-y divide-[#302840]/40">
                {filteredStock.map((s) => {
                  const isLow = s.quantity < 50;
                  const isModerate = s.quantity >= 50 && s.quantity < 100;
                  return (
                    <tr key={`${s.warehouse}-${s.sku}`} className="hover:bg-[#1e1e30]/50 transition-colors">
                      <td className="px-5 py-4 font-mono font-bold text-[#00ffcc] text-xs">
                        {s.sku}
                      </td>
                      <td className="px-5 py-4 text-[#e8e0f0] font-medium text-xs">
                        {s.name || s.sku}
                      </td>
                      <td className="px-5 py-4 text-[#a098b0] text-xs">
                        <div className="flex items-center gap-1.5">
                          <Warehouse size={13} className="text-[#ffe04a]" />
                          <span>{s.warehouse}</span>
                        </div>
                      </td>
                      <td className="px-5 py-4 text-[#a098b0] text-xs font-mono">{s.pack_size || "Standard"}</td>
                      <td className="px-5 py-4 text-right font-mono text-[#e8e0f0] text-xs">
                        ₹{s.mrp_inr?.toFixed(2) || "0.00"}
                      </td>
                      <td className="px-5 py-4 text-right font-headline font-bold text-xs">
                        <span
                          className={
                            isLow
                              ? "text-[#ff2d78]"
                              : isModerate
                              ? "text-[#ffe04a]"
                              : "text-[#00ffcc]"
                          }
                        >
                          {s.quantity.toLocaleString()}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-right">
                        <span
                          className={`text-[10px] font-label font-bold uppercase px-2.5 py-0.5 rounded-full border ${
                            isLow
                              ? "bg-[#ff2d78]/10 text-[#ff2d78] border-[#ff2d78]/30"
                              : isModerate
                              ? "bg-[#ffe04a]/10 text-[#ffe04a] border-[#ffe04a]/30"
                              : "bg-[#00ffcc]/10 text-[#00ffcc] border-[#00ffcc]/30"
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
                <Boxes className="mx-auto text-[#5a5068]" size={36} />
                <div className="text-sm text-[#e8e0f0] font-headline font-semibold">No SKUs found</div>
                <p className="text-xs text-[#a098b0] max-w-sm mx-auto">
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
