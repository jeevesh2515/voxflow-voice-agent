"use client";

import { useState } from "react";
import useSWR from "swr";
import Link from "next/link";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Clock,
  Ban,
  Activity,
  PhoneCall,
  RefreshCw,
  Search,
  Building2,
  ChevronRight,
  Sparkles,
} from "lucide-react";
import { api } from "@/lib/api";

type StatusFilter = "all" | "active" | "past_due" | "suspended" | "trialing";

export default function SuperadminDashboardPage() {
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [search, setSearch] = useState("");

  const { data, error, isLoading, mutate } = useSWR(
    "superadmin-tenants",
    () => api.superadminTenants(),
    { revalidateOnFocus: true, refreshInterval: 10000 }
  );

  const tenants = data?.tenants || [];

  const filteredTenants = tenants.filter((t) => {
    const matchesSearch =
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.tenant_id.toLowerCase().includes(search.toLowerCase());
    if (!matchesSearch) return false;
    if (filter === "all") return true;
    if (filter === "suspended") return t.subscription_status === "suspended";
    if (filter === "past_due") return t.subscription_status === "past_due";
    if (filter === "active") return t.subscription_status === "active";
    if (filter === "trialing") return t.subscription_status === "trialing";
    return true;
  });

  const activeCount = tenants.filter((t) => t.subscription_status === "active").length;
  const pastDueCount = tenants.filter((t) => t.subscription_status === "past_due").length;
  const suspendedCount = tenants.filter((t) => t.subscription_status === "suspended").length;
  const trialingCount = tenants.filter((t) => t.subscription_status === "trialing").length;

  return (
    <div className="min-h-screen bg-black text-neutral-100 p-6 md:p-10 font-sans selection:bg-rose-500/30">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-white/10 pb-6">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
                <ShieldAlert className="w-3.5 h-3.5" />
                Platform Superadmin Control Plane
              </span>
              <span className="text-xs text-neutral-500">· Phase 2 Revenue & Dunning</span>
            </div>
            <h1 className="text-3xl font-semibold tracking-tight text-white">
              Tenant Subscriptions & Governance
            </h1>
            <p className="text-sm text-neutral-400 mt-1">
              Live subscription states, automated dunning grace periods, and suspension telemetry.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => mutate()}
              disabled={isLoading}
              className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg bg-neutral-900 border border-white/10 hover:border-white/20 text-xs font-medium text-neutral-300 hover:text-white transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
              Refresh
            </button>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1 px-3.5 py-2 rounded-lg bg-white/5 border border-white/10 hover:border-white/20 text-xs font-medium text-neutral-300 hover:text-white transition-all"
            >
              Back to Dashboard
              <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>

        {/* Top KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="p-4 rounded-xl bg-neutral-950 border border-white/10">
            <div className="flex items-center justify-between text-xs text-neutral-400">
              <span>Total Workspaces</span>
              <Building2 className="w-4 h-4 text-neutral-500" />
            </div>
            <div className="text-2xl font-bold text-white mt-2">{tenants.length}</div>
            <div className="text-[11px] text-neutral-500 mt-1">
              {data?.total_calls ?? 0} calls processed
            </div>
          </div>

          <div className="p-4 rounded-xl bg-neutral-950 border border-emerald-500/20">
            <div className="flex items-center justify-between text-xs text-emerald-400">
              <span>Active Billing</span>
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold text-emerald-400 mt-2">{activeCount}</div>
            <div className="text-[11px] text-emerald-500/80 mt-1">Paid in good standing</div>
          </div>

          <div className="p-4 rounded-xl bg-neutral-950 border border-amber-500/20">
            <div className="flex items-center justify-between text-xs text-amber-400">
              <span>Grace Period (Past Due)</span>
              <AlertTriangle className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-2xl font-bold text-amber-400 mt-2">{pastDueCount}</div>
            <div className="text-[11px] text-amber-500/80 mt-1">Stripe retry in progress</div>
          </div>

          <div className="p-4 rounded-xl bg-neutral-950 border border-rose-500/20">
            <div className="flex items-center justify-between text-xs text-rose-400">
              <span>Auto-Suspended</span>
              <Ban className="w-4 h-4 text-rose-400" />
            </div>
            <div className="text-2xl font-bold text-rose-400 mt-2">{suspendedCount}</div>
            <div className="text-[11px] text-rose-500/80 mt-1">Dunning retries exhausted</div>
          </div>

          <div className="p-4 rounded-xl bg-neutral-950 border border-blue-500/20 col-span-2 md:col-span-1">
            <div className="flex items-center justify-between text-xs text-blue-400">
              <span>Trialing</span>
              <Clock className="w-4 h-4 text-blue-400" />
            </div>
            <div className="text-2xl font-bold text-blue-400 mt-2">{trialingCount}</div>
            <div className="text-[11px] text-blue-500/80 mt-1">14-day trial active</div>
          </div>
        </div>

        {/* Filter and Search Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-neutral-950/60 p-3 rounded-xl border border-white/10">
          <div className="flex items-center gap-1 w-full sm:w-auto overflow-x-auto pb-1 sm:pb-0">
            {(
              [
                { id: "all", label: "All Tenants", count: tenants.length },
                { id: "active", label: "Active", count: activeCount },
                { id: "past_due", label: "Grace Period", count: pastDueCount },
                { id: "suspended", label: "Suspended", count: suspendedCount },
                { id: "trialing", label: "Trialing", count: trialingCount },
              ] as const
            ).map((t) => (
              <button
                key={t.id}
                onClick={() => setFilter(t.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all flex items-center gap-1.5 ${
                  filter === t.id
                    ? "bg-white text-black font-semibold shadow-sm"
                    : "text-neutral-400 hover:text-white hover:bg-white/5"
                }`}
              >
                {t.label}
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                    filter === t.id ? "bg-black/20 text-black" : "bg-white/10 text-neutral-400"
                  }`}
                >
                  {t.count}
                </span>
              </button>
            ))}
          </div>

          <div className="relative w-full sm:w-72">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500" />
            <input
              type="text"
              placeholder="Search tenant name or ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-neutral-900 border border-white/10 rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder:text-neutral-500 focus:outline-none focus:border-rose-500/50"
            />
          </div>
        </div>

        {/* Tenants Table */}
        <div className="rounded-xl border border-white/10 bg-neutral-950 overflow-hidden shadow-2xl">
          {error ? (
            <div className="p-12 text-center">
              <ShieldAlert className="w-8 h-8 text-rose-400 mx-auto mb-3" />
              <div className="text-sm font-semibold text-white">Superadmin Access Restricted</div>
              <div className="text-xs text-neutral-400 mt-1 max-w-md mx-auto">
                {error instanceof Error ? error.message : "You must be authenticated as an authorized platform superadmin to view this page."}
              </div>
            </div>
          ) : isLoading ? (
            <div className="p-12 text-center">
              <RefreshCw className="w-6 h-6 text-neutral-500 animate-spin mx-auto mb-2" />
              <div className="text-xs text-neutral-400">Loading live tenant telemetry...</div>
            </div>
          ) : filteredTenants.length === 0 ? (
            <div className="p-12 text-center text-xs text-neutral-500">
              No tenants match the selected filter.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-white/10 bg-white/[0.02] text-neutral-400 uppercase tracking-wider text-[10px]">
                    <th className="py-3 px-4">Tenant / Workspace</th>
                    <th className="py-3 px-4">Plan Tier</th>
                    <th className="py-3 px-4">Billing Status</th>
                    <th className="py-3 px-4">Dunning / Failures</th>
                    <th className="py-3 px-4">Voice Minutes</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {filteredTenants.map((t) => {
                    const status = t.subscription_status || "trialing";
                    const isSuspended = status === "suspended";
                    const isPastDue = status === "past_due";
                    const isActive = status === "active";

                    return (
                      <tr
                        key={t.tenant_id}
                        className={`hover:bg-white/[0.02] transition-colors ${
                          isSuspended ? "bg-rose-500/[0.03]" : isPastDue ? "bg-amber-500/[0.02]" : ""
                        }`}
                      >
                        <td className="py-3.5 px-4">
                          <div className="flex items-center gap-2.5">
                            <div className="w-8 h-8 rounded-lg bg-neutral-900 border border-white/10 flex items-center justify-center font-bold text-neutral-300">
                              {t.name.charAt(0).toUpperCase()}
                            </div>
                            <div>
                              <div className="font-medium text-white flex items-center gap-1.5">
                                {t.name}
                                {isSuspended && (
                                  <span className="text-[10px] px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300 border border-rose-500/30">
                                    SUSPENDED
                                  </span>
                                )}
                              </div>
                              <div className="text-[11px] text-neutral-500 font-mono">
                                id: {t.tenant_id}
                              </div>
                            </div>
                          </div>
                        </td>

                        <td className="py-3.5 px-4">
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium uppercase tracking-wide bg-neutral-900 text-neutral-300 border border-white/10">
                            {t.plan || "starter"}
                          </span>
                        </td>

                        <td className="py-3.5 px-4">
                          {isActive && (
                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                              Active
                            </span>
                          )}
                          {isPastDue && (
                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20">
                              <AlertTriangle className="w-3 h-3" />
                              Grace Period (Past Due)
                            </span>
                          )}
                          {isSuspended && (
                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-rose-500/20 text-rose-300 border border-rose-500/30">
                              <Ban className="w-3 h-3" />
                              Suspended
                            </span>
                          )}
                          {!isActive && !isPastDue && !isSuspended && (
                            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
                              <Clock className="w-3 h-3" />
                              Trialing
                            </span>
                          )}
                        </td>

                        <td className="py-3.5 px-4">
                          {t.failed_payment_count > 0 ? (
                            <div className="text-rose-400 flex items-center gap-1 font-medium">
                              <AlertTriangle className="w-3.5 h-3.5" />
                              {t.failed_payment_count} failed attempt{t.failed_payment_count > 1 ? "s" : ""}
                            </div>
                          ) : (
                            <span className="text-neutral-500">0 failures</span>
                          )}
                        </td>

                        <td className="py-3.5 px-4">
                          <div className="text-white font-medium">
                            {t.minutes_used} min{t.minutes_used === 1 ? "" : "s"}
                          </div>
                          <div className="text-[11px] text-neutral-500">
                            {t.call_count} call{t.call_count === 1 ? "" : "s"}
                          </div>
                        </td>

                        <td className="py-3.5 px-4 text-right">
                          <Link
                            href={`/dashboard?tenant=${encodeURIComponent(t.tenant_id)}`}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-white/5 border border-white/10 hover:border-white/20 text-[11px] font-medium text-neutral-300 hover:text-white transition-all"
                          >
                            Inspect Workspace
                            <ChevronRight className="w-3 h-3" />
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Footer info note */}
        <div className="p-4 rounded-xl bg-neutral-950/40 border border-white/5 flex items-start gap-3 text-xs text-neutral-400">
          <Sparkles className="w-4 h-4 text-neutral-500 shrink-0 mt-0.5" />
          <div>
            <span className="text-neutral-300 font-medium">Automated Dunning Protocol:</span> When an invoice payment fails, the tenant enters a grace-period state (<code className="text-amber-400">past_due</code>) while Stripe retries according to Smart Retries. Once retries are exhausted, the tenant automatically transitions to <code className="text-rose-400">suspended</code>, halting automated voice operations until settled.
          </div>
        </div>
      </div>
    </div>
  );
}
