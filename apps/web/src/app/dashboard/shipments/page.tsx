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
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#12121e] p-6 rounded-2xl border border-[#242436] shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-mono text-[#94a3b8]">
            <span>Logistics & Dispatch</span>
            <span>/</span>
            <span className="text-[#00ffcc] font-bold">{activeTenant.name}</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-headline font-bold text-white tracking-tight">
            Shipment Telemetry & Carrier Tracking
          </h1>
          <p className="text-xs sm:text-sm text-[#94a3b8]">
            Real-time multi-carrier telemetry, dispatch milestones, and GPS ETA monitoring.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => refreshShipments()}
            className="bg-[#181826] hover:bg-[#202034] border border-[#2c2c40] px-4 py-2 rounded-xl text-xs font-medium flex items-center gap-2 text-[#cbd5e1] hover:text-white transition-colors"
          >
            <RefreshCw size={14} className="text-[#00ffcc]" />
            <span>Refresh Status</span>
          </button>
        </div>
      </header>

      {/* ==================== STAT CARDS ==================== */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Active Shipments</span>
            <Truck size={16} className="text-[#00ffcc]" />
          </div>
          <div className="text-2xl font-headline font-bold text-white">{stats.total}</div>
          <div className="text-xs text-[#00ffcc] mt-1">Live tracking active</div>
        </div>

        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>In Transit</span>
            <MapPin size={16} className="text-blue-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-blue-400">{stats.inTransit}</div>
          <div className="text-xs text-[#94a3b8] mt-1">On carrier network</div>
        </div>

        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Delivered (On-Time)</span>
            <CheckCircle2 size={16} className="text-emerald-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-emerald-400">{stats.delivered}</div>
          <div className="text-xs text-[#94a3b8] mt-1">99.4% SLA adherence</div>
        </div>

        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Exceptions / Delays</span>
            <AlertTriangle size={16} className="text-[#ff2d78]" />
          </div>
          <div className="text-2xl font-headline font-bold text-[#ff2d78]">{stats.delayed}</div>
          <div className="text-xs text-[#94a3b8] mt-1">Automated voice re-route</div>
        </div>
      </div>

      {/* ==================== FILTERS & SEARCH ==================== */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between bg-[#141422] p-3 rounded-2xl border border-[#28283c]">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#64748b]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search tracking number, order ID, carrier..."
            className="w-full bg-[#10101a] border border-[#28283c] rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder:text-[#64748b] focus:outline-none focus:border-[#00ffcc]"
          />
        </div>
        <div className="flex items-center bg-[#10101a] p-1 rounded-xl border border-[#28283c] overflow-x-auto">
          {["all", "bluedart", "delhivery", "dtdc", "ekart"].map((c) => (
            <button
              key={c}
              onClick={() => setCarrierFilter(c)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium uppercase tracking-wider transition-colors shrink-0 ${
                carrierFilter === c
                  ? "bg-[#ff2d78] text-white"
                  : "text-[#94a3b8] hover:text-white"
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
          <div className="py-16 text-center text-[#94a3b8] text-xs">
            Loading telemetry stream...
          </div>
        )}

        {error && (
          <div className="p-6 text-center text-red-400 bg-red-500/10 text-xs rounded-2xl border border-red-500/20">
            Failed to load shipments. Please verify backend API connectivity.
          </div>
        )}

        {!isLoading &&
          !error &&
          filteredShipments.map((s) => (
            <div
              key={s.id}
              className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] hover:border-[#00ffcc]/50 transition-all space-y-4 shadow-sm"
            >
              {/* Top row */}
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#00ffcc]/15 border border-[#00ffcc]/30 flex items-center justify-center text-[#00ffcc]">
                    <Truck size={20} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-headline font-bold text-sm text-white">{s.id}</span>
                      <span className="text-[10px] font-mono font-bold text-[#00ffcc] px-2 py-0.5 rounded bg-[#00ffcc]/10 border border-[#00ffcc]/30 uppercase">
                        {s.carrier}
                      </span>
                    </div>
                    <div className="text-xs text-[#94a3b8] font-mono mt-0.5">
                      Tracking: <strong className="text-white">{s.tracking_no}</strong> · Order:{" "}
                      <span className="text-[#ff2d78]">#{s.order_id}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] font-mono font-bold uppercase px-3 py-1 rounded-md border ${
                      s.status === "delivered"
                        ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                        : s.status === "in_transit"
                        ? "bg-blue-500/15 text-blue-400 border-blue-500/30"
                        : s.status === "delayed"
                        ? "bg-red-500/15 text-red-400 border-red-500/30"
                        : "bg-amber-500/15 text-amber-400 border-amber-500/30"
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
                          ? "bg-[#00ffcc]"
                          : "bg-[#181826] border border-[#28283c]"
                      }`}
                    />
                    <div
                      className={`text-[9px] font-mono uppercase tracking-wider ${
                        st.completed ? "text-[#00ffcc] font-bold" : "text-[#64748b]"
                      }`}
                    >
                      {st.step}
                    </div>
                  </div>
                ))}
              </div>

              {/* History events */}
              {s.history && s.history.length > 0 && (
                <div className="bg-[#181828] p-3 rounded-xl border border-[#28283c] space-y-2">
                  <div className="text-[10px] font-mono uppercase tracking-wider text-[#94a3b8] font-bold">
                    Recent Milestones
                  </div>
                  <div className="space-y-1.5">
                    {(s.history as Shipment["history"]).map((h, i) => (
                      <div key={i} className="flex justify-between items-center text-xs">
                        <div className="flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-[#00ffcc]" />
                          <span className="text-[#f1f5f9] font-medium">{h.note}</span>
                        </div>
                        <span className="text-[10px] font-mono text-[#94a3b8]">{fmtRelative(h.at)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* ETA Footer */}
              {s.expected_delivery && (
                <div className="flex items-center justify-between text-xs text-[#94a3b8] pt-1">
                  <div className="flex items-center gap-1.5">
                    <Calendar size={13} className="text-[#00ffcc]" />
                    <span>
                      Expected Delivery:{" "}
                      <strong className="text-white">
                        {new Date(s.expected_delivery).toLocaleDateString("en-IN", {
                          day: "numeric",
                          month: "short",
                          year: "numeric",
                        })}
                      </strong>
                    </span>
                  </div>
                  <span className="text-[10px] font-mono text-[#94a3b8]">
                    Updated {fmtRelative(s.last_update)}
                  </span>
                </div>
              )}
            </div>
          ))}

        {!isLoading && !error && filteredShipments.length === 0 && (
          <div className="bg-[#141422] rounded-2xl border border-dashed border-[#28283c] p-16 text-center space-y-3">
            <Truck className="mx-auto text-[#64748b]" size={36} />
            <div className="text-sm text-white font-headline font-semibold">No shipments recorded</div>
            <p className="text-xs text-[#94a3b8] max-w-sm mx-auto">
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
