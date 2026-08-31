"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import useSWR from "swr";
import {
  PhoneCall,
  Package,
  Users,
  Clock,
  Download,
  Plus,
  Mic,
  TrendingUp,
  Brain,
  Activity,
  Phone,
  ChevronRight,
  ArrowUpRight,
  ArrowDownRight,
  BarChart3,
  Zap,
  ShieldCheck,
} from "lucide-react";
import { api } from "@/lib/api";
import { fmtRelative } from "@/lib/format";
import { useTenant } from "@/lib/tenant-context";
import type { Call } from "@/lib/types";
import StatCard from "@/components/dashboard/StatCard";
import SectionCard from "@/components/dashboard/SectionCard";
import BarChart from "@/components/dashboard/BarChart";

export default function DashboardOverview() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: summary, error: summaryErr, isLoading: summaryLoading } = useSWR(["summary", activeTenantId], () => api.summary(activeTenantId));
  const { data: calls, error: callsErr, isLoading: callsLoading } = useSWR(["calls", activeTenantId], () => api.calls(100, activeTenantId));
  const { data: suppliers } = useSWR(["suppliers", activeTenantId], () => api.suppliers(undefined, activeTenantId));
  const { data: orders } = useSWR(["orders", activeTenantId], () => api.orders({ tenant_id: activeTenantId }));
  const { data: stock } = useSWR(["stock", activeTenantId], () => api.stock({ tenant_id: activeTenantId }));
  const { data: escalations } = useSWR(["escalations", activeTenantId], () => api.escalations(activeTenantId));

  const [activeKeypad, setActiveKeypad] = useState<string | null>(null);

  const handleKeyClick = (val: string) => {
    setActiveKeypad(val);
    setTimeout(() => setActiveKeypad(null), 200);
  };

  const isLoading = summaryLoading || callsLoading;

  const callVolumeData = useMemo(() => {
    if (!calls || calls.length === 0) return [];
    const last7 = Array.from({ length: 7 }, (_, i) => {
      const d = new Date();
      d.setDate(d.getDate() - (6 - i));
      return d.toISOString().split("T")[0];
    });

    const counts: Record<string, number> = {};
    calls.forEach((c) => {
      const day = c.started_at.split("T")[0];
      if (last7.includes(day)) {
        counts[day] = (counts[day] || 0) + 1;
      }
    });

    return last7.map((day) => ({
      label: new Date(day).toLocaleDateString("en-US", { weekday: "short" }),
      value: counts[day] || 0,
    }));
  }, [calls]);

  const resolutionRate = useMemo(() => {
    if (!calls || calls.length === 0) return 0;
    const resolved = calls.filter((c) => c.resolution_status === "resolved").length;
    return Math.round((resolved / calls.length) * 100);
  }, [calls]);

  const pendingOrdersCount = useMemo(() => {
    if (!orders) return 0;
    return orders.filter((o) => o.status === "pending" || o.status === "in_progress").length;
  }, [orders]);

  const lowStockCount = useMemo(() => {
    if (!stock) return 0;
    return stock.filter((s) => s.quantity < 50).length;
  }, [stock]);

  const escalationCount = useMemo(() => {
    if (!escalations) return 0;
    return escalations.filter((c) => c.escalated || c.follow_up_required).length;
  }, [escalations]);

  const urgentCalls = useMemo(() => {
    if (!calls) return [];
    return calls.filter((c) => c.outcome === "in_progress" || c.escalated).slice(0, 5);
  }, [calls]);

  const recentCalls = useMemo(() => {
    if (!calls) return [];
    return [...calls].sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime()).slice(0, 8);
  }, [calls]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* ==================== PAGE HEADER ==================== */}
      <div className="px-6 pt-6 pb-2">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-[#e8e0f0] tracking-tight">
              Operations <span className="text-[#ff2d78]">Overview</span>
            </h1>
            <p className="text-[#a098b0] text-sm mt-1.5">
              Real-time telephonic logistics engine for <strong className="text-[#e8e0f0]">{activeTenant.name}</strong>.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => window.open("/api/calls/export", "_blank")}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#28283e] border border-[#302840] text-xs font-bold uppercase tracking-widest text-[#e8e0f0] hover:border-[#00ffcc] transition-all"
            >
              <Download size={14} className="text-[#00ffcc]" /> Export
            </button>
            <Link
              href="/dashboard/simulator"
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#ff2d78] text-[#1a0010] text-xs font-bold uppercase tracking-widest hover:scale-105 active:scale-95 transition-all shadow-[0_0_16px_rgba(255,45,120,0.3)]"
            >
              <Plus size={14} /> New Campaign
            </Link>
          </div>
        </div>
      </div>

      {isLoading && (
        <div className="px-6">
          <div className="rounded-xl border border-[#302840]/30 bg-[#141422]/40 p-8 text-center">
            <div className="inline-flex items-center gap-2 text-[#a098b0] text-sm">
              <div className="w-4 h-4 border-2 border-[#ff2d78] border-t-transparent rounded-full animate-spin" />
              Loading dashboard...
            </div>
          </div>
        </div>
      )}

      {summaryErr && (
        <div className="px-6">
          <div className="rounded-xl border border-danger-500/30 bg-danger-500/10 p-4 text-sm text-danger-400">
            Failed to load dashboard data. Is the API running?
          </div>
        </div>
      )}

      {!isLoading && !summaryErr && (
        <>
          {/* ==================== STAT CARDS ROW ==================== */}
          <div className="px-6 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
            <StatCard
              title="Total Calls"
              value={summary?.calls != null ? Number(summary.calls).toLocaleString() : "—"}
              icon={<PhoneCall size={20} />}
              accent="primary"
              trend={{ value: "12.5%", positive: true }}
            />
            <StatCard
              title="Pending Orders"
              value={summary?.pending_orders != null ? summary.pending_orders : "—"}
              icon={<Package size={20} />}
              accent="secondary"
              trend={{ value: "2.4%", positive: false }}
            />
            <StatCard
              title="Suppliers"
              value={summary?.suppliers != null ? summary.suppliers : "—"}
              icon={<Users size={20} />}
              accent="neutral"
            />
            <StatCard
              title="Last Call"
              value={summary?.last_call_at ? "Completed" : "No calls yet"}
              icon={<Clock size={20} />}
              accent="tertiary"
              subtitle={summary?.last_call_at ? fmtRelative(summary.last_call_at) : undefined}
            />
          </div>

          {/* ==================== MAIN DASHBOARD GRID ==================== */}
          <div className="px-6 grid grid-cols-12 gap-6">
            {/* Left Column */}
            <div className="col-span-12 xl:col-span-8 space-y-6">
              {/* Call Volume Chart */}
              <SectionCard
                title="Call Volume (7 Days)"
                subtitle="Daily call activity trend"
                icon={<BarChart3 size={18} className="text-[#00ffcc]" />}
                action={
                  <span className="text-[10px] font-mono text-[#a098b0] uppercase tracking-wider">
                    {calls?.length ?? 0} total calls
                  </span>
                }
              >
                <div className="h-[180px]">
                  <BarChart data={callVolumeData} height={140} color="#00ffcc" />
                </div>
              </SectionCard>

              {/* Active & Recent Interactions Table */}
              <SectionCard
                title="Recent Interactions"
                subtitle="Latest call logs across your workspace"
                icon={<Activity size={18} className="text-[#ff2d78]" />}
                action={
                  <Link
                    href="/dashboard/calls"
                    className="text-xs font-bold uppercase tracking-widest text-[#a098b0] hover:text-[#ff2d78] transition-colors flex items-center gap-1"
                  >
                    View All <ChevronRight size={14} />
                  </Link>
                }
              >
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead className="text-[10px] font-mono uppercase tracking-widest text-[#a098b0] border-b border-[#302840]/40">
                      <tr>
                        <th className="px-4 py-3 text-left font-medium">ID</th>
                        <th className="px-4 py-3 text-left font-medium">Participant</th>
                        <th className="px-4 py-3 text-left font-medium">Type</th>
                        <th className="px-4 py-3 text-left font-medium">Status</th>
                        <th className="px-4 py-3 text-left font-medium">Time</th>
                        <th className="px-4 py-3 text-right font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#302840]/30">
                      {recentCalls.map((c) => (
                        <tr key={c.id} className="hover:bg-[#1e1e30]/30 transition-colors">
                          <td className="px-4 py-3">
                            <span className="text-xs font-mono text-[#ff2d78] font-bold">#{c.id.slice(0, 8)}</span>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex flex-col">
                              <span className="text-sm font-medium text-[#e8e0f0]">{c.caller_name || "Regional Agent"}</span>
                              <span className="text-[10px] font-mono text-[#a098b0]">{c.caller_phone || "+91 9811..."}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-[10px] font-mono uppercase tracking-wider text-[#a098b0] px-2 py-0.5 rounded border border-[#302840]/40 bg-[#1e1e30]/30">
                              {c.intent || "Order Verification"}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${c.outcome === "completed" ? "text-success-400 border-success-500/30 bg-success-500/10" : c.outcome === "in_progress" ? "text-warn-400 border-warn-500/30 bg-warn-500/10" : "text-[#a098b0] border-[#302840]/40 bg-[#1e1e30]/30"}`}>
                              {c.outcome || "COMPLETED"}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-xs text-[#a098b0] font-mono">{fmtRelative(c.started_at)}</td>
                          <td className="px-4 py-3 text-right">
                            <Link
                              href="/dashboard/calls"
                              className="text-[10px] font-bold uppercase tracking-widest text-[#00ffcc] hover:text-[#00ffcc]/80 transition-colors"
                            >
                              Details
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </SectionCard>
            </div>

            {/* Right Side Panel */}
            <div className="col-span-12 xl:col-span-4 space-y-6">
              {/* Phone Simulator Widget */}
              <SectionCard
                title="Phone Simulator"
                icon={<Phone size={18} className="text-[#ff2d78]" />}
              >
                <div className="bg-[#0a0a12] border border-[#302840]/60 rounded-xl p-5 mb-4">
                  <div className="flex flex-col items-center py-6">
                    <div className="w-16 h-16 rounded-full bg-[#ff2d78]/10 border border-[#ff2d78]/30 flex items-center justify-center mb-3 text-[#ff2d78] shadow-[0_0_24px_rgba(255,45,120,0.2)]">
                      <Mic size={28} />
                    </div>
                    <p className="text-[10px] font-mono uppercase tracking-[0.2em] text-[#a098b0]">Ready to Sim</p>
                    <p className="text-base font-bold text-[#e8e0f0] mt-1">VoxFlow Agent Alpha</p>
                  </div>

                  {/* 3x4 Dialpad Grid */}
                  <div className="grid grid-cols-3 gap-2">
                    {["1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "0", "#"].map((digit) => (
                      <button
                        key={digit}
                        onClick={() => handleKeyClick(digit)}
                        className={`
                          h-11 rounded-lg border font-bold text-sm transition-all duration-150
                          ${activeKeypad === digit
                            ? "bg-[#ff2d78]/30 border-[#ff2d78] text-[#ff2d78] scale-95 shadow-[0_0_12px_rgba(255,45,120,0.3)]"
                            : "bg-[#1e1e30] border-[#302840] text-[#e8e0f0] hover:border-[#ff2d78]/40 hover:bg-[#28283e]"
                          }
                        `}
                      >
                        {digit}
                      </button>
                    ))}
                  </div>
                </div>

                <Link
                  href="/dashboard/simulator"
                  className="w-full py-3 bg-[#ff2d78] text-[#1a0010] font-bold text-sm rounded-xl flex items-center justify-center gap-2 hover:scale-[1.02] active:scale-[0.98] transition-all shadow-[0_0_16px_rgba(255,45,120,0.3)]"
                >
                  <Phone size={16} /> Start Simulation
                </Link>
              </SectionCard>

              {/* AI Health Index */}
              <SectionCard
                title="AI Health Index"
                subtitle="Real-time agent performance"
                icon={<Brain size={18} className="text-[#ff2d78]" />}
              >
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between items-center text-[10px] font-mono uppercase tracking-widest text-[#a098b0] mb-2">
                      <span>Resolution Rate</span>
                      <span className="text-[#ff2d78] font-bold text-sm">{resolutionRate}%</span>
                    </div>
                    <div className="h-2 w-full bg-[#ff2d78]/10 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-[#ff2d78] to-[#ff2d78]/70 rounded-full transition-all duration-700"
                        style={{ width: `${resolutionRate}%` }}
                      />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-[#0a0a12] rounded-lg p-3 border border-[#302840]/40">
                      <div className="text-[10px] font-mono uppercase tracking-wider text-[#a098b0] mb-1">Avg Duration</div>
                      <div className="text-lg font-bold text-[#e8e0f0]">
                        {calls && calls.length > 0
                          ? `${Math.round(calls.reduce((sum, c) => sum + c.duration_sec, 0) / calls.length)}s`
                          : "—"}
                      </div>
                    </div>
                    <div className="bg-[#0a0a12] rounded-lg p-3 border border-[#302840]/40">
                      <div className="text-[10px] font-mono uppercase tracking-wider text-[#a098b0] mb-1">Escalations</div>
                      <div className="text-lg font-bold text-[#e8e0f0]">{escalationCount}</div>
                    </div>
                    <div className="bg-[#0a0a12] rounded-lg p-3 border border-[#302840]/40">
                      <div className="text-[10px] font-mono uppercase tracking-wider text-[#a098b0] mb-1">Satisfaction</div>
                      <div className="text-lg font-bold text-[#00ffcc]">
                        {calls && calls.length > 0
                          ? `${Math.round((calls.filter(c => c.satisfaction === "happy").length / calls.length) * 100)}%`
                          : "—"}
                      </div>
                    </div>
                    <div className="bg-[#0a0a12] rounded-lg p-3 border border-[#302840]/40">
                      <div className="text-[10px] font-mono uppercase tracking-wider text-[#a098b0] mb-1">Verified</div>
                      <div className="text-lg font-bold text-[#e8e0f0]">
                        {calls && calls.length > 0
                          ? `${Math.round((calls.filter(c => c.verified).length / calls.length) * 100)}%`
                          : "—"}
                      </div>
                    </div>
                  </div>
                </div>
              </SectionCard>

              {/* Urgent Items */}
              <SectionCard
                title="Urgent Items"
                icon={<Zap size={18} className="text-[#ff4444]" />}
                action={
                  <Link href="/dashboard/escalations" className="text-[10px] font-bold uppercase tracking-widest text-[#a098b0] hover:text-[#ff2d78] transition-colors">
                    View All
                  </Link>
                }
              >
                <div className="space-y-2.5">
                  {urgentCalls.length === 0 ? (
                    <div className="text-center py-6">
                      <ShieldCheck size={24} className="mx-auto text-success-500 mb-2" />
                      <p className="text-xs text-[#a098b0]">No urgent items right now</p>
                    </div>
                  ) : (
                    urgentCalls.map((c) => (
                      <div
                        key={c.id}
                        className={`p-3.5 rounded-lg border-l-[3px] ${
                          c.escalated
                            ? "border-l-[#ff2d78] bg-[#ff2d78]/5"
                            : "border-l-[#ffe04a] bg-[#ffe04a]/5"
                        }`}
                      >
                        <div className="flex justify-between items-start mb-1">
                          <span className="text-xs font-mono font-bold text-[#e8e0f0]">#{c.id.slice(0, 10)}</span>
                          <span className="text-[10px] text-[#a098b0]">{c.caller_name || "Unknown"}</span>
                        </div>
                        <p className="text-[11px] text-[#a098b0] leading-relaxed">
                          {c.escalated ? "Escalated — needs human review" : "Call in progress — agent handling"}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </SectionCard>

              {/* Registered Suppliers */}
              <SectionCard
                title="Registered Suppliers"
                icon={<Users size={18} className="text-[#ffe04a]" />}
                action={
                  <Link href="/dashboard/suppliers" className="text-[10px] font-bold uppercase tracking-widest text-[#00ffcc] hover:text-[#00ffcc]/80 transition-colors">
                    View All
                  </Link>
                }
              >
                <div className="space-y-2.5">
                  {(suppliers as Array<{ id: string; name: string; city: string; phone: string }> | undefined)?.slice(0, 5).map((s) => (
                    <Link
                      key={s.id}
                      href="/dashboard/suppliers"
                      className="flex items-center gap-3 p-2 rounded-lg hover:bg-[#1e1e30]/40 transition-colors group"
                    >
                      <div className="w-9 h-9 rounded-lg bg-[#28283e] border border-[#302840] flex items-center justify-center text-[#ff2d78] font-bold text-xs shrink-0">
                        {s.name.charAt(0)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-[#e8e0f0] group-hover:text-[#ff2d78] transition-colors truncate">{s.name}</p>
                        <p className="text-[10px] text-[#a098b0] font-mono">{s.city} · {s.phone}</p>
                      </div>
                      <ChevronRight size={14} className="text-[#a098b0] group-hover:text-[#e8e0f0] transition-colors shrink-0" />
                    </Link>
                  ))}
                  {(!suppliers || suppliers.length === 0) && (
                    <div className="text-xs text-[#5a5068] text-center py-4">No suppliers registered yet.</div>
                  )}
                </div>
              </SectionCard>
            </div>
          </div>

          {/* ==================== BENTO ROW - Quick Stats ==================== */}
          <div className="px-6 grid grid-cols-1 sm:grid-cols-3 gap-4">
            <SectionCard
              title="Orders"
              subtitle={`${orders?.length ?? 0} total`}
              icon={<Package size={18} className="text-[#00ffcc]" />}
              action={
                <Link href="/dashboard/orders" className="text-[10px] font-bold uppercase tracking-widest text-[#00ffcc] hover:text-[#00ffcc]/80">
                  View All →
                </Link>
              }
            >
              <div className="flex items-end justify-between">
                <div>
                  <div className="text-2xl font-bold text-[#e8e0f0]">{orders?.length ?? 0}</div>
                  <div className="text-[10px] text-[#a098b0] font-mono mt-1">{pendingOrdersCount} pending</div>
                </div>
                <div className="text-right">
                  <div className="text-2xl font-bold text-[#e8e0f0]">{stock?.length ?? 0}</div>
                  <div className="text-[10px] text-[#a098b0] font-mono mt-1">{lowStockCount} low stock</div>
                </div>
              </div>
            </SectionCard>

            <SectionCard
              title="System Health"
              icon={<Activity size={18} className="text-[#00ffcc]" />}
            >
              <div className="flex items-center gap-3">
                <div className="relative w-16 h-16">
                  <svg className="w-16 h-16 -rotate-90" viewBox="0 0 64 64">
                    <circle cx="32" cy="32" r="28" fill="none" stroke="#302840" strokeWidth="6" />
                    <circle cx="32" cy="32" r="28" fill="none" stroke="#00ffcc" strokeWidth="6" strokeDasharray={`${2 * Math.PI * 28 * 0.98}`} strokeLinecap="round" />
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-sm font-bold text-[#00ffcc]">98%</span>
                  </div>
                </div>
                <div>
                  <p className="text-xs text-[#e8e0f0] font-medium">All systems operational</p>
                  <p className="text-[10px] text-[#a098b0] font-mono mt-1">API · WS · DB</p>
                </div>
              </div>
            </SectionCard>

            <SectionCard
              title="Quick Actions"
              icon={<Zap size={18} className="text-[#ffe04a]" />}
            >
              <div className="flex flex-wrap gap-2">
                <Link href="/dashboard/simulator" className="px-3 py-1.5 rounded-lg bg-[#1e1e30] border border-[#302840] text-[10px] font-bold uppercase tracking-wider text-[#e8e0f0] hover:border-[#ff2d78] transition-all">
                  New Call
                </Link>
                <Link href="/dashboard/calls" className="px-3 py-1.5 rounded-lg bg-[#1e1e30] border border-[#302840] text-[10px] font-bold uppercase tracking-wider text-[#e8e0f0] hover:border-[#00ffcc] transition-all">
                  View Logs
                </Link>
                <Link href="/dashboard/escalations" className="px-3 py-1.5 rounded-lg bg-[#1e1e30] border border-[#302840] text-[10px] font-bold uppercase tracking-wider text-[#e8e0f0] hover:border-[#ffe04a] transition-all">
                  Escalations
                </Link>
              </div>
            </SectionCard>
          </div>
        </>
      )}
    </div>
  );
}
