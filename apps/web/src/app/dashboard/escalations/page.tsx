"use client";

import React, { useState, useMemo } from "react";
import useSWR, { mutate } from "swr";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  ShieldAlert,
  ShieldCheck,
  ShieldOff,
  Search,
  User,
  UserCheck,
  RotateCw,
  Filter,
  Check,
  FileText,
  Activity,
  ArrowRight,
  TrendingUp,
} from "lucide-react";
import { api } from "@/lib/api";
import { fmtRelative, fmtTime } from "@/lib/format";
import { useTenant } from "@/lib/tenant-context";
import type { Call, EscalationPriority, EscalationStatus } from "@/lib/types";
import SectionCard from "@/components/dashboard/SectionCard";
import { ResolutionDrawer } from "@/components/dashboard/ResolutionDrawer";

export default function EscalationsPage() {
  const { activeTenantId, activeTenant } = useTenant();

  // Filters state
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [priorityFilter, setPriorityFilter] = useState<string>("all");
  const [breachedOnly, setBreachedOnly] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedCallForResolution, setSelectedCallForResolution] = useState<Call | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [assigningId, setAssigningId] = useState<string | null>(null);

  // SWR queries
  const escalationsKey = [
    "escalations",
    activeTenantId,
    statusFilter,
    priorityFilter,
    breachedOnly,
    searchQuery,
  ];

  const {
    data: escalationsRes,
    error: escalationsError,
    isLoading: isEscalationsLoading,
  } = useSWR(escalationsKey, () =>
    api.getEscalations(activeTenantId, {
      status: statusFilter,
      priority: priorityFilter,
      breached_only: breachedOnly,
      search: searchQuery || undefined,
    })
  );

  const { data: metrics, isLoading: isMetricsLoading } = useSWR(
    ["escalation-metrics", activeTenantId],
    () => api.getEscalationMetrics(activeTenantId),
    { refreshInterval: 15000 }
  );

  const calls = escalationsRes?.items || [];

  const refreshAll = () => {
    mutate(escalationsKey);
    mutate(["escalation-metrics", activeTenantId]);
  };

  const handleClaimTicket = async (callId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setAssigningId(callId);
    try {
      await api.assignEscalation(activeTenantId, callId, "operator");
      refreshAll();
    } catch (err) {
      console.error("Failed to claim ticket", err);
    } finally {
      setAssigningId(null);
    }
  };

  const openResolution = (call: Call) => {
    setSelectedCallForResolution(call);
    setIsDrawerOpen(true);
  };

  const getPriorityBadge = (p?: EscalationPriority) => {
    switch (p) {
      case "critical":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
            <AlertTriangle className="w-3 h-3" /> Critical
          </span>
        );
      case "high":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-3 h-3" /> High
          </span>
        );
      case "low":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Clock className="w-3 h-3" /> Low
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Clock className="w-3 h-3" /> Medium
          </span>
        );
    }
  };

  const getStatusBadge = (status?: EscalationStatus, isResolvedStaff?: boolean) => {
    const s = status === "none" && isResolvedStaff ? "resolved" : status || "pending";
    switch (s) {
      case "in_progress":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
            <UserCheck className="w-3 h-3" /> In Progress
          </span>
        );
      case "resolved":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3 h-3" /> Resolved
          </span>
        );
      case "dismissed":
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-zinc-800 text-zinc-400 border border-zinc-700">
            Dismissed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium bg-amber-500/10 text-amber-300 border border-amber-500/20">
            <Clock className="w-3 h-3" /> Action Required
          </span>
        );
    }
  };

  const [currentTime, setCurrentTime] = useState<number>(0);

  React.useEffect(() => {
    setCurrentTime(Date.now());
    const interval = setInterval(() => {
      setCurrentTime(Date.now());
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const renderSLACountdown = (call: Call) => {
    if (!call.sla_due_at) return null;
    if (call.escalation_status === "resolved" || call.escalation_status === "dismissed") {
      return (
        <span className="text-[11px] font-mono text-zinc-400">
          Resolved {call.staff_resolved_at ? fmtRelative(call.staff_resolved_at) : ""}
        </span>
      );
    }

    if (currentTime === 0) return null;

    const dueTime = new Date(call.sla_due_at).getTime();
    const diffMs = dueTime - currentTime;
    const isBreached = diffMs < 0;
    const diffMins = Math.abs(Math.round(diffMs / 60000));

    if (isBreached) {
      return (
        <span className="inline-flex items-center gap-1 text-xs font-semibold text-rose-400 bg-rose-950/60 px-2 py-0.5 rounded-full border border-rose-800 animate-pulse">
          <ShieldAlert className="w-3 h-3" /> Breached {diffMins}m ago
        </span>
      );
    }

    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-300 bg-amber-950/30 px-2 py-0.5 rounded-full border border-amber-800/40">
        <Clock className="w-3 h-3" /> Due in {diffMins}m
      </span>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header & KPI Metrics */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800/80">
          <div className="text-xs font-mono uppercase tracking-wider text-zinc-400 mb-1">Open Queue</div>
          <div className="text-2xl font-bold text-zinc-100 flex items-baseline gap-1.5">
            {metrics ? metrics.open_count : isMetricsLoading ? "-" : 0}
            <span className="text-xs font-normal text-amber-400">active</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800/80">
          <div className="text-xs font-mono uppercase tracking-wider text-zinc-400 mb-1">SLA Breaches</div>
          <div className={`text-2xl font-bold flex items-baseline gap-1.5 ${(metrics?.breached_count || 0) > 0 ? "text-rose-400" : "text-zinc-100"}`}>
            {metrics ? metrics.breached_count : isMetricsLoading ? "-" : 0}
            {(metrics?.breached_count || 0) > 0 && (
              <span className="text-xs font-medium text-rose-400 animate-pulse">action needed</span>
            )}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800/80">
          <div className="text-xs font-mono uppercase tracking-wider text-zinc-400 mb-1">SLA Adherence</div>
          <div className="text-2xl font-bold text-zinc-100 flex items-baseline gap-1.5">
            {metrics ? `${metrics.sla_compliance_rate}%` : isMetricsLoading ? "-" : "100%"}
            <span className="text-xs font-normal text-emerald-400">target &gt;95%</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800/80">
          <div className="text-xs font-mono uppercase tracking-wider text-zinc-400 mb-1">Avg Resolution</div>
          <div className="text-2xl font-bold text-zinc-100 flex items-baseline gap-1.5">
            {metrics ? `${metrics.avg_resolution_min}m` : isMetricsLoading ? "-" : "0m"}
            <span className="text-xs font-normal text-zinc-400">per ticket</span>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-zinc-900/60 border border-zinc-800/80 col-span-2 lg:col-span-1">
          <div className="text-xs font-mono uppercase tracking-wider text-zinc-400 mb-1">Total Resolved</div>
          <div className="text-2xl font-bold text-emerald-400 flex items-baseline gap-1.5">
            {metrics ? metrics.resolved_count : isMetricsLoading ? "-" : 0}
            <span className="text-xs font-normal text-zinc-400">tickets</span>
          </div>
        </div>
      </div>

      {/* Main Section */}
      <SectionCard
        title="Escalations & Operator Queue"
        subtitle={`${activeTenant.name} · Real-time SLA tracking & closed-loop resolution`}
        icon={<AlertTriangle size={18} className="text-[#ff4444]" />}
        action={
          <div className="flex items-center gap-3">
            <button
              onClick={refreshAll}
              className="p-2 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-zinc-100 transition-colors"
              title="Refresh queue"
            >
              <RotateCw className="w-4 h-4" />
            </button>
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search caller, phone, reason..."
                className="pl-9 pr-4 py-1.5 rounded-lg bg-zinc-950 border border-zinc-800 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 w-48 sm:w-64"
              />
            </div>
          </div>
        }
      >
        {/* Filters Bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 pb-4 mb-4 border-b border-zinc-800/60">
          <div className="flex flex-wrap items-center gap-1.5">
            {[
              { id: "all", label: "All Tickets" },
              { id: "open", label: "Open (Action Needed)" },
              { id: "pending", label: "Unclaimed" },
              { id: "in_progress", label: "In Progress" },
              { id: "resolved", label: "Resolved" },
              { id: "dismissed", label: "Dismissed" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setStatusFilter(tab.id)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  statusFilter === tab.id
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "bg-zinc-900/60 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60 border border-zinc-800/60"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-3">
            {/* Priority filter */}
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="bg-zinc-900 border border-zinc-800 rounded-lg px-2.5 py-1.5 text-xs text-zinc-300 focus:outline-none focus:border-indigo-500"
            >
              <option value="all">All Priorities</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>

            {/* Breached Only Toggle */}
            <button
              onClick={() => setBreachedOnly(!breachedOnly)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                breachedOnly
                  ? "bg-rose-950/60 border-rose-800 text-rose-300"
                  : "bg-zinc-900/60 border-zinc-800/60 text-zinc-400 hover:text-zinc-200"
              }`}
            >
              <ShieldAlert className="w-3.5 h-3.5" />
              Breached Only
            </button>
          </div>
        </div>

        {/* Queue List Content */}
        {isEscalationsLoading && (
          <div className="text-center text-zinc-400 py-16 text-sm flex items-center justify-center gap-2">
            <Activity className="w-4 h-4 animate-spin text-indigo-400" />
            Loading escalation queue…
          </div>
        )}

        {escalationsError && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            Failed to load escalations. Please check backend connection.
          </div>
        )}

        {!isEscalationsLoading && !escalationsError && calls.length > 0 && (
          <div className="space-y-3">
            {calls.map((call) => {
              const isResolved = call.escalation_status === "resolved" || Boolean(call.staff_resolved_at);
              return (
                <div
                  key={call.id}
                  onClick={() => openResolution(call)}
                  className={`group rounded-xl border p-4 sm:p-5 transition-all cursor-pointer hover:border-zinc-700 ${
                    isResolved
                      ? "border-zinc-800/40 bg-zinc-900/20 opacity-75"
                      : "border-zinc-800 bg-zinc-900/40 hover:bg-zinc-900/60 shadow-sm"
                  }`}
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-zinc-800/80 border border-zinc-700/80 flex items-center justify-center text-xs font-mono font-bold text-zinc-200 shrink-0">
                        {call.language ? call.language.toUpperCase() : "EN"}
                      </div>
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-semibold text-zinc-100 group-hover:text-indigo-300 transition-colors">
                            {call.caller_name || call.caller_phone || "Unknown Caller"}
                          </span>
                          {call.caller_name && (
                            <span className="text-xs font-mono text-zinc-400">{call.caller_phone}</span>
                          )}
                          {call.verified ? (
                            <span className="flex items-center gap-1 text-[10px] font-mono text-zinc-400 border border-zinc-800 bg-zinc-900/60 px-1.5 py-0.5 rounded">
                              <ShieldCheck size={10} className="text-emerald-400" /> verified
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-[10px] font-mono text-amber-400 border border-amber-500/20 bg-amber-500/10 px-1.5 py-0.5 rounded">
                              <ShieldOff size={10} /> unverified
                            </span>
                          )}
                        </div>
                        <div className="text-[11px] text-zinc-400 flex items-center gap-2 mt-0.5">
                          <Clock size={11} />
                          <span>Started {fmtRelative(call.started_at)}</span>
                          <span className="text-zinc-600">·</span>
                          <span>{call.duration_sec || 0}s duration</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-start sm:self-center flex-wrap">
                      {getPriorityBadge(call.escalation_priority)}
                      {getStatusBadge(call.escalation_status, Boolean(call.staff_resolved_at))}
                      {renderSLACountdown(call)}
                    </div>
                  </div>

                  {/* Reason & Solution Preview */}
                  {(call.reason || call.solution) && (
                    <div className="rounded-lg bg-zinc-950/60 border border-zinc-800/80 p-3 mb-3 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                      {call.reason && (
                        <div>
                          <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 block mb-0.5">
                            Escalation Reason:
                          </span>
                          <span className="text-zinc-200 line-clamp-2">{call.reason}</span>
                        </div>
                      )}
                      {call.solution && (
                        <div>
                          <span className="text-[10px] font-mono uppercase tracking-wider text-zinc-400 block mb-0.5">
                            Agent Proposed Action:
                          </span>
                          <span className="text-zinc-300 line-clamp-2">{call.solution}</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Staff Resolution Notes (if resolved) */}
                  {isResolved && call.staff_resolution && (
                    <div className="rounded-lg bg-emerald-950/20 border border-emerald-800/30 p-3 mb-3 text-xs">
                      <div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-wider text-emerald-400 mb-1">
                        <span>Staff Resolution ({call.resolution_category || "Standard"})</span>
                        {call.resolved_by_user_id && <span>By {call.resolved_by_user_id}</span>}
                      </div>
                      <p className="text-zinc-200">{call.staff_resolution}</p>
                    </div>
                  )}

                  {/* Action Row */}
                  <div className="flex items-center justify-between pt-2 border-t border-zinc-800/40 text-xs">
                    <div className="flex items-center gap-2">
                      {call.assigned_to_user_id ? (
                        <span className="inline-flex items-center gap-1 text-xs text-indigo-300">
                          <UserCheck className="w-3.5 h-3.5" /> Assigned to {call.assigned_to_user_id}
                        </span>
                      ) : !isResolved ? (
                        <button
                          type="button"
                          onClick={(e) => handleClaimTicket(call.id, e)}
                          disabled={assigningId === call.id}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-xs font-medium transition-colors"
                        >
                          <User className="w-3 h-3" />
                          {assigningId === call.id ? "Claiming…" : "Claim Ticket"}
                        </button>
                      ) : null}
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          openResolution(call);
                        }}
                        className={`inline-flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                          isResolved
                            ? "bg-zinc-800 hover:bg-zinc-700 text-zinc-300"
                            : "bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm"
                        }`}
                      >
                        {isResolved ? "View / Edit Resolution" : "Resolve Escalation"}
                        <ArrowRight className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {!isEscalationsLoading && !escalationsError && calls.length === 0 && (
          <div className="px-4 py-16 text-center">
            <CheckCircle2 size={36} className="mx-auto text-emerald-400 mb-3" />
            <div className="text-base font-semibold text-zinc-100">
              No Escalations in {activeTenant.name} Queue
            </div>
            <div className="text-xs text-zinc-400 mt-1 max-w-sm mx-auto">
              All caller requests and issues are currently resolved. Incoming escalated calls will appear here automatically.
            </div>
          </div>
        )}
      </SectionCard>

      {/* Resolution Drawer */}
      <ResolutionDrawer
        call={selectedCallForResolution}
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        onResolved={(updated) => {
          refreshAll();
        }}
        tenantId={activeTenantId}
      />
    </div>
  );
}
