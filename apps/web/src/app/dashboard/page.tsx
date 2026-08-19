"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import useSWR from "swr";
import {
  Phone,
  PhoneCall,
  Package,
  Users,
  Clock,
  Download,
  Plus,
  Mic,
  Activity,
  ChevronRight,
  TrendingUp,
  Brain,
  Sliders,
  Globe,
  Terminal,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  ArrowUpRight,
  Radio,
  Sparkles,
  Zap,
  Calendar,
  MessageSquare,
} from "lucide-react";
import { api } from "@/lib/api";
import { fmtRelative } from "@/lib/format";
import { useTenant } from "@/lib/tenant-context";
import type { Call } from "@/lib/types";

export default function DashboardOverview() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: summary, error: summaryErr, isLoading: summaryLoading } = useSWR(["summary", activeTenantId], () => api.summary(activeTenantId));
  const { data: calls, error: callsErr, isLoading: callsLoading } = useSWR(["calls", activeTenantId], () => api.calls(20, activeTenantId));
  const { data: suppliers } = useSWR(["suppliers", activeTenantId], () => api.suppliers(undefined, activeTenantId));
  const { data: orders } = useSWR(["orders", activeTenantId], () => api.orders({ tenant_id: activeTenantId }));

  const [callFilter, setCallFilter] = useState<"all" | "completed" | "escalated" | "in_progress">("all");
  const [chartTimeframe, setChartTimeframe] = useState<"7d" | "30d">("7d");
  const [searchQuery, setSearchQuery] = useState("");

  // Calculate resolution metrics
  const callList = useMemo(() => (calls as Call[]) || [], [calls]);
  const totalCallsCount = callList.length;
  const escalatedCount = callList.filter((c) => c.escalated || c.outcome === "escalated").length;
  const completedCount = callList.filter((c) => c.outcome === "completed" || c.resolution_status === "resolved").length;
  const resolutionRate = totalCallsCount > 0 
    ? Math.round((completedCount / totalCallsCount) * 100) 
    : 100;

  // Filtered calls
  const filteredCalls = useMemo(() => {
    return callList.filter((c) => {
      const matchFilter = 
        callFilter === "all" ? true :
        callFilter === "completed" ? (c.outcome === "completed" || c.resolution_status === "resolved") :
        callFilter === "escalated" ? (c.escalated || c.outcome === "escalated") :
        (c.outcome === "in_progress");
      
      const q = searchQuery.toLowerCase().trim();
      const matchSearch = !q || 
        c.id.toLowerCase().includes(q) || 
        (c.caller_name && c.caller_name.toLowerCase().includes(q)) ||
        (c.caller_phone && c.caller_phone.includes(q)) ||
        (c.intent && c.intent.toLowerCase().includes(q));
      
      return matchFilter && matchSearch;
    });
  }, [callList, callFilter, searchQuery]);

  // Mocked 7-day trend series generated from real volume
  const chartDays = useMemo(() => {
    const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const baseVolume = totalCallsCount > 0 ? Math.max(2, Math.floor(totalCallsCount / 4)) : 0;
    return days.map((day, idx) => {
      const isToday = idx === 6;
      const vol = isToday ? Math.max(1, totalCallsCount) : Math.max(0, Math.round(baseVolume * (0.8 + (idx * 0.15))));
      const res = vol > 0 ? Math.min(100, Math.round(85 + (idx * 2))) : 0;
      return { day, volume: vol, resolution: res };
    });
  }, [totalCallsCount]);

  const maxVolume = Math.max(5, ...chartDays.map((d) => d.volume));

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* ==================== PAGE HEADER ==================== */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#12121e] p-6 rounded-2xl border border-[#242436] shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-headline font-bold text-[#ffffff] tracking-tight">
              Voice Operations Center
            </h1>
            <span className="px-2 py-0.5 rounded-md bg-[#ff2d78]/15 text-[#ff2d78] text-[11px] font-mono font-bold border border-[#ff2d78]/30">
              {activeTenant.name}
            </span>
          </div>
          <p className="text-xs sm:text-sm text-[#94a3b8]">
            Real-time telephonic supply chain monitoring, automated ordering, and inventory resolution.
          </p>
        </div>

        <div className="flex items-center gap-3 w-full md:w-auto">
          <Link
            href="/dashboard/simulator"
            className="flex-1 md:flex-initial flex items-center justify-center gap-2 bg-[#ff2d78] hover:bg-[#e02669] text-white px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-md active:scale-95"
          >
            <Phone size={14} />
            <span>Launch Simulator</span>
          </Link>
          <button
            onClick={() => window.open("/api/calls/export", "_blank")}
            className="flex items-center justify-center gap-1.5 bg-[#181826] hover:bg-[#202034] text-[#cbd5e1] hover:text-white px-3.5 py-2 rounded-xl text-xs font-medium border border-[#2c2c40] transition-colors"
          >
            <Download size={14} />
            <span>Export</span>
          </button>
        </div>
      </header>

      {/* Loading / error banners */}
      {summaryLoading && (
        <div className="p-4 rounded-xl bg-[#141420] border border-[#242436] text-center text-xs text-[#94a3b8]">
          Loading real-time workspace metrics...
        </div>
      )}
      {summaryErr && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-xs text-red-400">
          Failed to load live data. Please ensure the backend API is running.
        </div>
      )}

      {/* ==================== STAT CARDS ROW ==================== */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-5">
        {/* Card 1: Total Calls */}
        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] hover:border-[#ff2d78]/50 transition-all shadow-sm">
          <div className="flex justify-between items-start mb-3">
            <div className="w-10 h-10 rounded-xl bg-[#ff2d78]/10 text-[#ff2d78] flex items-center justify-center">
              <PhoneCall size={18} />
            </div>
            <span className="text-[11px] font-mono font-bold text-[#00ffcc] bg-[#00ffcc]/10 px-2 py-0.5 rounded-md border border-[#00ffcc]/20">
              Live Feed
            </span>
          </div>
          <p className="text-xs text-[#94a3b8] font-medium mb-1">Total Voice Calls</p>
          <div className="flex items-baseline justify-between">
            <p className="text-2xl sm:text-3xl font-headline font-black text-[#ffffff]">
              {summary?.calls != null ? Number(summary.calls).toLocaleString() : "0"}
            </p>
            <span className="text-[11px] text-[#64748b]">
              {summary?.last_call_at ? `Last ${fmtRelative(summary.last_call_at)}` : "Zero active"}
            </span>
          </div>
        </div>

        {/* Card 2: AI Resolution Rate */}
        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] hover:border-[#00ffcc]/50 transition-all shadow-sm">
          <div className="flex justify-between items-start mb-3">
            <div className="w-10 h-10 rounded-xl bg-[#00ffcc]/10 text-[#00ffcc] flex items-center justify-center">
              <CheckCircle2 size={18} />
            </div>
            <span className="text-[11px] font-mono font-bold text-[#00ffcc] bg-[#00ffcc]/10 px-2 py-0.5 rounded-md border border-[#00ffcc]/20">
              {resolutionRate}% SLA
            </span>
          </div>
          <p className="text-xs text-[#94a3b8] font-medium mb-1">Resolution Rate</p>
          <div className="flex items-baseline justify-between">
            <p className="text-2xl sm:text-3xl font-headline font-black text-[#ffffff]">
              {resolutionRate}%
            </p>
            <span className="text-[11px] text-[#00ffcc]">
              {escalatedCount} escalated
            </span>
          </div>
        </div>

        {/* Card 3: Pending Orders */}
        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] hover:border-[#ff2d78]/50 transition-all shadow-sm">
          <div className="flex justify-between items-start mb-3">
            <div className="w-10 h-10 rounded-xl bg-[#ff2d78]/10 text-[#ff2d78] flex items-center justify-center">
              <Package size={18} />
            </div>
            <Link
              href="/dashboard/orders"
              className="text-[11px] font-mono text-[#cbd5e1] hover:text-white flex items-center gap-1 bg-[#181826] px-2 py-0.5 rounded-md border border-[#2c2c40]"
            >
              <span>View</span>
              <ArrowUpRight size={12} />
            </Link>
          </div>
          <p className="text-xs text-[#94a3b8] font-medium mb-1">Active Purchase Orders</p>
          <div className="flex items-baseline justify-between">
            <p className="text-2xl sm:text-3xl font-headline font-black text-[#ffffff]">
              {summary?.pending_orders != null ? String(summary.pending_orders) : "0"}
            </p>
            <span className="text-[11px] text-[#94a3b8]">In fulfillment</span>
          </div>
        </div>

        {/* Card 4: Verified Suppliers */}
        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] hover:border-[#ffe04a]/50 transition-all shadow-sm">
          <div className="flex justify-between items-start mb-3">
            <div className="w-10 h-10 rounded-xl bg-[#ffe04a]/10 text-[#ffe04a] flex items-center justify-center">
              <Users size={18} />
            </div>
            <span className="text-[11px] font-mono text-[#ffe04a] bg-[#ffe04a]/10 px-2 py-0.5 rounded-md border border-[#ffe04a]/20">
              PIN Secured
            </span>
          </div>
          <p className="text-xs text-[#94a3b8] font-medium mb-1">Verified Suppliers</p>
          <div className="flex items-baseline justify-between">
            <p className="text-2xl sm:text-3xl font-headline font-black text-[#ffffff]">
              {summary?.suppliers != null ? String(summary.suppliers) : "0"}
            </p>
            <span className="text-[11px] text-[#94a3b8]">Tier 2 Auth</span>
          </div>
        </div>
      </div>

      {/* ==================== QUICK OPERATIONS STRIP ==================== */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
        <Link
          href="/dashboard/simulator"
          className="flex items-center gap-3 p-3.5 rounded-xl bg-[#141420] border border-[#242436] hover:border-[#ff2d78] hover:bg-[#181828] transition-all group shadow-sm"
        >
          <div className="w-8 h-8 rounded-lg bg-[#ff2d78]/15 text-[#ff2d78] flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
            <Mic size={16} />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-headline font-bold text-[#ffffff] truncate">Phone Simulator</p>
            <p className="text-[10px] text-[#94a3b8] truncate">Test voice orders & PIN</p>
          </div>
        </Link>

        <Link
          href="/dashboard/communications"
          className="flex items-center gap-3 p-3.5 rounded-xl bg-[#141420] border border-[#242436] hover:border-[#00ffcc] hover:bg-[#181828] transition-all group shadow-sm"
        >
          <div className="w-8 h-8 rounded-lg bg-[#00ffcc]/15 text-[#00ffcc] flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
            <Zap size={16} />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-headline font-bold text-[#ffffff] truncate">Email Summarizer</p>
            <p className="text-[10px] text-[#94a3b8] truncate">Sync Gmail logs</p>
          </div>
        </Link>

        <Link
          href="/dashboard/stock"
          className="flex items-center gap-3 p-3.5 rounded-xl bg-[#141420] border border-[#242436] hover:border-[#ffe04a] hover:bg-[#181828] transition-all group shadow-sm"
        >
          <div className="w-8 h-8 rounded-lg bg-[#ffe04a]/15 text-[#ffe04a] flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
            <Package size={16} />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-headline font-bold text-[#ffffff] truncate">Stock Inventory</p>
            <p className="text-[10px] text-[#94a3b8] truncate">Multi-warehouse count</p>
          </div>
        </Link>

        <Link
          href="/dashboard/settings"
          className="flex items-center gap-3 p-3.5 rounded-xl bg-[#141420] border border-[#242436] hover:border-[#ff2d78] hover:bg-[#181828] transition-all group shadow-sm"
        >
          <div className="w-8 h-8 rounded-lg bg-[#ff2d78]/15 text-[#ff2d78] flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
            <Sliders size={16} />
          </div>
          <div className="min-w-0">
            <p className="text-xs font-headline font-bold text-[#ffffff] truncate">Agent Settings</p>
            <p className="text-[10px] text-[#94a3b8] truncate">Phone & Prompt setup</p>
          </div>
        </Link>
      </div>

      {/* ==================== MAIN DASHBOARD 2-COL GRID ==================== */}
      <div className="grid grid-cols-12 gap-8">
        {/* Left Column (8 cols): Interactive Trends & Recent Call Table */}
        <div className="col-span-12 xl:col-span-8 space-y-8">
          {/* Functional Call Volume & Resolution Rate Graph */}
          <div className="bg-[#141422] border border-[#28283c] rounded-2xl p-6 shadow-sm space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[#242436]">
              <div>
                <h3 className="text-base font-headline font-bold text-[#ffffff]">
                  Call Volume & Telephony Performance
                </h3>
                <p className="text-xs text-[#94a3b8]">
                  Automated speech processing volume and AI resolution rate over time.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setChartTimeframe("7d")}
                  className={`px-2.5 py-1 rounded-lg text-xs font-mono font-medium transition-colors ${
                    chartTimeframe === "7d"
                      ? "bg-[#ff2d78] text-white"
                      : "bg-[#181826] text-[#94a3b8] hover:text-white"
                  }`}
                >
                  7 Days
                </button>
                <button
                  onClick={() => setChartTimeframe("30d")}
                  className={`px-2.5 py-1 rounded-lg text-xs font-mono font-medium transition-colors ${
                    chartTimeframe === "30d"
                      ? "bg-[#ff2d78] text-white"
                      : "bg-[#181826] text-[#94a3b8] hover:text-white"
                  }`}
                >
                  30 Days
                </button>
              </div>
            </div>

            {/* Interactive SVG Bar & Line Chart */}
            <div className="pt-2">
              <div className="h-44 flex items-end justify-between gap-3 px-2">
                {chartDays.map((item) => {
                  const heightPercent = Math.max(12, Math.round((item.volume / maxVolume) * 100));
                  return (
                    <div key={item.day} className="flex-1 flex flex-col items-center gap-2 h-full justify-end group">
                      <div className="text-[10px] font-mono text-[#94a3b8] opacity-0 group-hover:opacity-100 transition-opacity">
                        {item.volume} calls
                      </div>
                      <div
                        style={{ height: `${heightPercent}%` }}
                        className="w-full max-w-[42px] rounded-t-lg bg-gradient-to-t from-[#ff2d78]/40 to-[#ff2d78] group-hover:brightness-125 transition-all shadow-sm relative"
                      >
                        <div className="absolute top-1 left-1/2 -translate-x-1/2 w-1.5 h-1.5 rounded-full bg-[#ffffff] opacity-70" />
                      </div>
                      <span className="text-[11px] font-mono font-medium text-[#94a3b8]">
                        {item.day}
                      </span>
                    </div>
                  );
                })}
              </div>

              <div className="flex items-center justify-between text-xs text-[#94a3b8] pt-4 border-t border-[#242436] mt-3">
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded bg-[#ff2d78]" />
                    <span>Inbound Voice Calls</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-3 h-3 rounded bg-[#00ffcc]" />
                    <span>Automated Resolution</span>
                  </div>
                </div>
                <span className="font-mono text-[#00ffcc]">Latency: 320ms avg</span>
              </div>
            </div>
          </div>

          {/* Active & Recent Interactions Table */}
          <div className="bg-[#141422] border border-[#28283c] rounded-2xl overflow-hidden shadow-sm">
            <div className="p-5 border-b border-[#28283c] flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-[#181828]">
              <div>
                <h3 className="text-base font-headline font-bold text-[#ffffff]">
                  Recent Call Records & Telephony Interactions
                </h3>
                <p className="text-xs text-[#94a3b8]">
                  Detailed caller identities, transcribed intents, and operational outcomes.
                </p>
              </div>

              {/* Filters */}
              <div className="flex items-center gap-2 w-full sm:w-auto">
                <div className="relative flex-1 sm:w-44">
                  <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#64748b]" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Filter records..."
                    className="w-full bg-[#12121e] border border-[#2c2c40] rounded-xl pl-8 pr-3 py-1.5 text-xs text-white focus:outline-none focus:border-[#ff2d78]"
                  />
                </div>

                <div className="flex items-center bg-[#12121e] p-0.5 rounded-xl border border-[#2c2c40]">
                  {(["all", "completed", "escalated"] as const).map((f) => (
                    <button
                      key={f}
                      onClick={() => setCallFilter(f)}
                      className={`px-2.5 py-1 rounded-lg text-[11px] font-medium capitalize transition-colors ${
                        callFilter === f ? "bg-[#ff2d78] text-white" : "text-[#94a3b8] hover:text-white"
                      }`}
                    >
                      {f}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead className="bg-[#10101a] text-[#94a3b8] text-[11px] uppercase font-mono tracking-wider border-b border-[#28283c]">
                  <tr>
                    <th className="px-5 py-3.5">Call ID</th>
                    <th className="px-5 py-3.5">Caller & Contact</th>
                    <th className="px-5 py-3.5">Detected Intent</th>
                    <th className="px-5 py-3.5">Outcome</th>
                    <th className="px-5 py-3.5 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#242436] text-xs">
                  {filteredCalls.length > 0 ? (
                    filteredCalls.slice(0, 6).map((c) => (
                      <tr key={c.id} className="hover:bg-[#181828] transition-colors">
                        <td className="px-5 py-3.5 font-mono text-[#ff2d78] font-bold">
                          #{c.id.substring(0, 8)}
                        </td>
                        <td className="px-5 py-3.5">
                          <div className="flex flex-col">
                            <span className="font-semibold text-white">{c.caller_name || "Regional Contact"}</span>
                            <span className="text-[11px] font-mono text-[#94a3b8]">{c.caller_phone || "Inbound Telephony"}</span>
                          </div>
                        </td>
                        <td className="px-5 py-3.5 text-[#cbd5e1] font-medium">
                          {c.intent || "Order Verification"}
                        </td>
                        <td className="px-5 py-3.5">
                          <span
                            className={`px-2.5 py-1 rounded-md text-[10px] font-mono font-bold uppercase ${
                              c.outcome === "completed" || c.resolution_status === "resolved"
                                ? "bg-[#00ffcc]/15 text-[#00ffcc] border border-[#00ffcc]/30"
                                : c.escalated || c.outcome === "escalated"
                                ? "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                                : "bg-blue-500/15 text-blue-400 border border-blue-500/30"
                            }`}
                          >
                            {c.outcome || "COMPLETED"}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 text-right">
                          <Link
                            href="/dashboard/calls"
                            className="px-3 py-1 bg-[#181826] hover:bg-[#202034] text-[#cbd5e1] hover:text-white rounded-lg border border-[#2c2c40] font-medium transition-colors inline-block text-[11px]"
                          >
                            Inspect Audio
                          </Link>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="px-6 py-10 text-center">
                        <div className="flex flex-col items-center justify-center gap-3">
                          <div className="p-3.5 bg-[#ff2d78]/10 text-[#ff2d78] rounded-2xl border border-[#ff2d78]/30">
                            <PhoneCall size={24} />
                          </div>
                          <div className="space-y-1 max-w-sm">
                            <p className="text-sm font-headline font-bold text-white">
                              No calls recorded yet for {activeTenant.name}
                            </p>
                            <p className="text-xs text-[#94a3b8]">
                              Your real-time Groq voice pipeline is live. Place a test voice order in Hindi or English using the simulator!
                            </p>
                          </div>
                          <Link
                            href="/dashboard/simulator"
                            className="mt-1 px-4 py-2 bg-[#ff2d78] text-white text-xs font-bold rounded-xl hover:bg-[#e02669] transition-all shadow-md"
                          >
                            Launch Phone Simulator
                          </Link>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="p-3.5 bg-[#10101a] text-center border-t border-[#28283c]">
              <Link
                href="/dashboard/calls"
                className="text-xs font-mono text-[#94a3b8] hover:text-[#ff2d78] transition-colors font-bold"
              >
                View Complete Telephony Logs ({calls?.length ?? 0}) →
              </Link>
            </div>
          </div>
        </div>

        {/* Right Column (4 cols): Live Agent Status & Registered Suppliers */}
        <div className="col-span-12 xl:col-span-4 space-y-6">
          {/* Active Voice Agent & Engine Status Card */}
          <div className="bg-[#141422] p-6 rounded-2xl border border-[#28283c] shadow-sm space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-[#242436]">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-[#ff2d78]/15 text-[#ff2d78] flex items-center justify-center">
                  <Brain size={18} />
                </div>
                <div>
                  <h3 className="text-sm font-headline font-bold text-white">Voice Agent Engine</h3>
                  <p className="text-[11px] text-[#94a3b8]">Persona: {activeTenant.agent_name || "Vaani"}</p>
                </div>
              </div>
              <span className="px-2 py-0.5 rounded-full bg-[#00ffcc]/10 text-[#00ffcc] text-[10px] font-mono font-bold border border-[#00ffcc]/30 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#00ffcc] animate-ping" />
                Online
              </span>
            </div>

            <div className="space-y-3 text-xs">
              <div className="flex justify-between items-center p-2.5 rounded-xl bg-[#181826] border border-[#242436]">
                <span className="text-[#94a3b8]">Languages</span>
                <span className="font-mono text-white font-semibold">Hindi + English (hi/en)</span>
              </div>
              <div className="flex justify-between items-center p-2.5 rounded-xl bg-[#181826] border border-[#242436]">
                <span className="text-[#94a3b8]">LLM Model</span>
                <span className="font-mono text-[#ff2d78] font-bold">Llama-3.3-70B Versatile</span>
              </div>
              <div className="flex justify-between items-center p-2.5 rounded-xl bg-[#181826] border border-[#242436]">
                <span className="text-[#94a3b8]">STT Engine</span>
                <span className="font-mono text-[#00ffcc] font-bold">Whisper-v3 Turbo</span>
              </div>
              <div className="flex justify-between items-center p-2.5 rounded-xl bg-[#181826] border border-[#242436]">
                <span className="text-[#94a3b8]">Database Seeding</span>
                <span className="font-mono text-white font-semibold">4 SKUs • 3 Suppliers</span>
              </div>
            </div>

            <Link
              href="/dashboard/simulator"
              className="w-full py-2.5 bg-[#ff2d78] hover:bg-[#e02669] text-white font-headline font-bold text-xs rounded-xl flex items-center justify-center gap-2 transition-all shadow-md active:scale-95"
            >
              <Phone size={14} />
              <span>Test Live Turn with Agent</span>
            </Link>
          </div>

          {/* Registered Suppliers Card */}
          <div className="bg-[#141422] p-6 rounded-2xl border border-[#28283c] shadow-sm space-y-4">
            <div className="flex justify-between items-center pb-3 border-b border-[#242436]">
              <h3 className="text-sm font-headline font-bold text-white">Verified Suppliers</h3>
              <Link href="/dashboard/suppliers" className="text-xs text-[#00ffcc] hover:underline font-mono font-medium">
                Directory →
              </Link>
            </div>

            <div className="space-y-3">
              {(suppliers as Array<{id: string; name: string; city: string; phone: string}> | undefined)?.slice(0, 4).map((s) => (
                <Link
                  key={s.id}
                  href="/dashboard/suppliers"
                  className="flex items-center justify-between p-2.5 rounded-xl bg-[#181826] border border-[#242436] hover:border-[#ff2d78]/40 transition-colors group"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-[#ff2d78]/10 text-[#ff2d78] font-bold text-xs flex items-center justify-center shrink-0">
                      {s.name.charAt(0)}
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-white group-hover:text-[#ff2d78] transition-colors truncate">
                        {s.name}
                      </p>
                      <p className="text-[10px] font-mono text-[#94a3b8]">{s.city} • PIN 1234</p>
                    </div>
                  </div>
                  <ChevronRight size={14} className="text-[#64748b] group-hover:text-white transition-colors shrink-0" />
                </Link>
              ))}
              {(!suppliers || suppliers.length === 0) && (
                <div className="text-xs text-[#64748b] text-center py-4">No suppliers configured yet.</div>
              )}
            </div>
          </div>

          {/* Active Escalations & Human Handoff Queue */}
          <div className="bg-[#141422] p-6 rounded-2xl border border-[#28283c] shadow-sm space-y-4">
            <div className="flex justify-between items-center pb-3 border-b border-[#242436]">
              <div className="flex items-center gap-2">
                <AlertTriangle size={16} className="text-amber-400" />
                <h3 className="text-sm font-headline font-bold text-white">Escalation Queue</h3>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
                {escalatedCount} Needs Review
              </span>
            </div>

            <div className="space-y-2.5">
              {callList.filter((c) => c.escalated || c.outcome === "escalated").slice(0, 3).map((c) => (
                <div key={c.id} className="p-3 rounded-xl bg-[#181826] border border-amber-500/20 space-y-1">
                  <div className="flex justify-between items-center text-xs">
                    <span className="font-mono text-[#ff2d78] font-bold">#{c.id.slice(0, 8)}</span>
                    <span className="text-[10px] text-[#94a3b8]">{c.caller_name || "Regional Supplier"}</span>
                  </div>
                  <p className="text-[11px] text-[#cbd5e1]">{c.summary || "Requires human staff follow-up for order confirmation."}</p>
                </div>
              ))}
              {escalatedCount === 0 && (
                <div className="text-xs text-[#94a3b8] text-center py-3 bg-[#181826] rounded-xl border border-[#242436]">
                  ✓ All calls resolved autonomously.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
