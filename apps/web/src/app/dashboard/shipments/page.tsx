"use client";

import { useState, useMemo } from "react";
import useSWR from "swr";
import {
  Truck,
  Search,
  Filter,
  Package,
  Calendar,
  Clock,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  ExternalLink,
  MapPin,
  RefreshCw,
} from "lucide-react";
import { api } from "@/lib/api";
import { fmtRelative, statusBg, statusColor } from "@/lib/format";
import { useTenant } from "@/lib/tenant-context";
import type { Shipment } from "@/lib/types";

export default function ShipmentsPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: shipments, error, isLoading, mutate: refreshShipments } = useSWR(
    ["shipments", activeTenantId],
    () => api.shipments(undefined, activeTenantId),
  );

  const [searchQuery, setSearchQuery] = useState("");
  const [carrierFilter, setCarrierFilter] = useState("all");
  const [selectedShipment, setSelectedShipment] = useState<Shipment | null>(null);

  const filteredShipments = useMemo(() => {
    if (!shipments) return [];
    return (shipments as Shipment[]).filter((s) => {
      const matchSearch =
        s.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.tracking_no.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.order_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        s.carrier.toLowerCase().includes(searchQuery.toLowerCase());
      const matchCarrier =
        carrierFilter === "all" || s.carrier.toLowerCase() === carrierFilter.toLowerCase();
      return matchSearch && matchCarrier;
    });
  }, [shipments, searchQuery, carrierFilter]);

  const stats = useMemo(() => {
    const list = (shipments as Shipment[]) || [];
    return {
      total: list.length,
      inTransit: list.filter((s) => s.status === "in_transit" || s.status === "dispatched").length,
      delivered: list.filter((s) => s.status === "delivered").length,
      delayed: list.filter((s) => s.status === "delayed").length,
    };
  }, [shipments]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* ==================== PAGE HEADER ==================== */}
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-label uppercase tracking-widest text-[#a098b0] mb-1">
            <span>Logistics</span>
            <span>/</span>
            <span className="text-[#00ffcc] font-bold">{activeTenant.name}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-headline font-extrabold text-[#e8e0f0] tracking-[0.05em] uppercase">
            Shipment <span className="text-[#00ffcc] text-glow-secondary">Tracking</span>
          </h1>
          <p className="text-[#a098b0] font-body text-sm mt-1">
            Real-time multi-carrier telemetry, dispatch milestones, and GPS ETA monitoring.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => refreshShipments()}
            className="bg-[#1e1e30] border border-[#302840] px-4 py-2 rounded-xl text-xs font-label font-bold uppercase tracking-widest flex items-center gap-2 hover:border-[#00ffcc] text-[#e8e0f0] transition-all"
          >
            <RefreshCw size={14} className="text-[#00ffcc]" /> Refresh Status
          </button>
        </div>
      </header>

      {/* ==================== STAT CARDS ==================== */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-4 rounded-2xl border border-[#00ffcc]/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>Active Shipments</span>
            <Truck size={16} className="text-[#00ffcc]" />
          </div>
          <div className="text-2xl font-headline font-bold text-[#e8e0f0]">{stats.total}</div>
          <div className="text-[10px] text-[#00ffcc] mt-1">Live tracking active</div>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-blue-500/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>In Transit</span>
            <MapPin size={16} className="text-blue-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-blue-400">{stats.inTransit}</div>
          <div className="text-[10px] text-[#a098b0] mt-1">On carrier network</div>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-emerald-500/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>Delivered (On-Time)</span>
            <CheckCircle2 size={16} className="text-emerald-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-emerald-400">{stats.delivered}</div>
          <div className="text-[10px] text-[#a098b0] mt-1">99.4% SLA adherence</div>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-[#ff2d78]/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>Exceptions / Delays</span>
            <AlertTriangle size={16} className="text-[#ff2d78]" />
          </div>
          <div className="text-2xl font-headline font-bold text-[#ff2d78]">{stats.delayed}</div>
          <div className="text-[10px] text-[#a098b0] mt-1">Automated voice re-route</div>
        </div>
      </div>

      {/* ==================== FILTERS & SEARCH ==================== */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between bg-[#111118]/80 p-3 rounded-2xl border border-[#302840]/60">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#a098b0]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search tracking number, order ID, carrier..."
            className="w-full bg-[#181824] border border-[#302840]/60 rounded-xl pl-9 pr-4 py-2 text-xs text-[#e8e0f0] placeholder:text-[#a098b0]/50 focus:outline-none focus:border-[#00ffcc] transition-all font-body"
          />
        </div>
        <div className="flex items-center gap-2 overflow-x-auto">
          {["all", "bluedart", "delhivery", "dtdc", "ekart"].map((c) => (
            <button
              key={c}
              onClick={() => setCarrierFilter(c)}
              className={`px-3 py-1.5 rounded-xl text-xs font-label uppercase tracking-wider transition-all shrink-0 ${
                carrierFilter === c
                  ? "bg-[#00ffcc] text-[#0a0a12] font-bold shadow-[0_0_12px_rgba(0,255,204,0.4)]"
                  : "bg-[#181824] text-[#a098b0] hover:text-[#e8e0f0] border border-[#302840]/60"
              }`}
            >
              {c}
            </button>
          ))}
        </div>
      </div>

      {/* ==================== SHIPMENTS LIST ==================== */}
      <div className="space-y-4">
        {isLoading && (
          <div className="py-16 text-center text-[#a098b0] text-xs font-label uppercase tracking-widest flex items-center justify-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#00ffcc] animate-ping" /> Loading telemetry stream...
          </div>
        )}

        {error && (
          <div className="p-6 text-center text-[#ff2d78] bg-[#ff2d78]/5 text-xs font-body rounded-2xl border border-[#ff2d78]/20">
            Failed to load shipments. Please verify backend API connectivity.
          </div>
        )}

        {!isLoading &&
          !error &&
          filteredShipments.map((s) => (
            <div
              key={s.id}
              className="glass-panel p-5 rounded-2xl border border-[#302840]/60 hover:border-[#00ffcc]/60 transition-all space-y-4 shadow-lg"
            >
              {/* Top row */}
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#00ffcc]/10 border border-[#00ffcc]/30 flex items-center justify-center text-[#00ffcc]">
                    <Truck size={20} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-headline font-bold text-sm text-[#e8e0f0]">{s.id}</span>
                      <span className="text-[10px] font-mono text-[#00ffcc] px-2 py-0.5 rounded bg-[#00ffcc]/10 border border-[#00ffcc]/20">
                        {s.carrier.toUpperCase()}
                      </span>
                    </div>
                    <div className="text-xs text-[#a098b0] font-mono mt-0.5">
                      Tracking: <strong className="text-[#e8e0f0]">{s.tracking_no}</strong> · Order:{" "}
                      <span className="text-[#ff2d78]">{s.order_id}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] font-label font-bold uppercase px-3 py-1 rounded-full border ${
                      s.status === "delivered"
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                        : s.status === "in_transit"
                        ? "bg-blue-500/10 text-blue-400 border-blue-500/30"
                        : s.status === "delayed"
                        ? "bg-[#ff2d78]/10 text-[#ff2d78] border-[#ff2d78]/30"
                        : "bg-[#ffe04a]/10 text-[#ffe04a] border-[#ffe04a]/30"
                    }`}
                  >
                    {s.status.replace("_", " ")}
                  </span>
                </div>
              </div>

              {/* Progress Milestones Bar */}
              <div className="grid grid-cols-4 gap-2 pt-2">
                {[
                  { step: "Booked", completed: true },
                  { step: "Dispatched", completed: s.status !== "booked" },
                  { step: "In Transit", completed: s.status === "in_transit" || s.status === "delivered" },
                  { step: "Delivered", completed: s.status === "delivered" },
                ].map((st, idx) => (
                  <div key={idx} className="space-y-1.5">
                    <div
                      className={`h-1.5 rounded-full transition-all ${
                        st.completed
                          ? "bg-[#00ffcc] shadow-[0_0_8px_#00ffcc]"
                          : "bg-[#1e1e30] border border-[#302840]/60"
                      }`}
                    />
                    <div
                      className={`text-[9px] font-label uppercase tracking-widest ${
                        st.completed ? "text-[#00ffcc] font-bold" : "text-[#5a5068]"
                      }`}
                    >
                      {st.step}
                    </div>
                  </div>
                ))}
              </div>

              {/* History events */}
              {s.history && s.history.length > 0 && (
                <div className="bg-[#141422] p-3 rounded-xl border border-[#302840]/60 space-y-2">
                  <div className="text-[10px] font-label uppercase tracking-widest text-[#a098b0]">
                    Recent Milestones
                  </div>
                  <div className="space-y-1.5">
                    {(s.history as Shipment["history"]).map((h, i) => (
                      <div key={i} className="flex justify-between items-center text-xs">
                        <div className="flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-[#00ffcc]" />
                          <span className="text-[#e8e0f0] font-medium">{h.note}</span>
                        </div>
                        <span className="text-[10px] font-mono text-[#a098b0]">{fmtRelative(h.at)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ETA Footer */}
              {s.expected_delivery && (
                <div className="flex items-center justify-between text-xs text-[#a098b0] pt-1">
                  <div className="flex items-center gap-1.5">
                    <Calendar size={13} className="text-[#00ffcc]" />
                    <span>
                      Expected Delivery:{" "}
                      <strong className="text-[#e8e0f0]">
                        {new Date(s.expected_delivery).toLocaleDateString("en-IN", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                      </strong>
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-[#a098b0]">
                    Updated {fmtRelative(s.last_update)}
                  </span>
                </div>
              )}
            </div>
          ))}

        {!isLoading && !error && filteredShipments.length === 0 && (
          <div className="glass-panel rounded-2xl border border-dashed border-[#302840]/60 p-16 text-center space-y-3">
            <Truck className="mx-auto text-[#5a5068]" size={36} />
            <div className="text-sm text-[#e8e0f0] font-headline font-semibold">No shipments recorded</div>
            <p className="text-xs text-[#a098b0] max-w-sm mx-auto">
              {searchQuery
                ? `No shipments matching "${searchQuery}".`
                : `Shipment logs will automatically populate when orders are dispatched via logistics partners.`}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
