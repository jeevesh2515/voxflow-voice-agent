"use client";

import { useState, useMemo } from "react";
import useSWR from "swr";
import { PhoneCall, ShieldCheck, ShieldOff, AlertCircle, Search, Filter, ChevronDown } from "lucide-react";
import { api } from "@/lib/api";
import { fmtRelative, fmtDuration, statusBg, statusColor } from "@/lib/format";
import { useTenant } from "@/lib/tenant-context";
import type { Call, CallTurn, CallAction, ResolutionStatus, Satisfaction } from "@/lib/types";
import SectionCard from "@/components/dashboard/SectionCard";
import DataTable from "@/components/dashboard/DataTable";

function satisfactionBadge(s: Satisfaction) {
  if (!s) return null;
  if (s === "happy")
    return (
      <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded border border-success-500/30 bg-success-500/10 text-success-500">
        happy
      </span>
    );
  if (s === "unhappy")
    return (
      <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded border border-danger-500/30 bg-danger-500/10 text-danger-500">
        unhappy
      </span>
    );
  return (
    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded border border-[#5a5068]/60 bg-[#1e1e30]/60 text-[#a098b0]">
      neutral
    </span>
  );
}

function resolutionBadge(r: ResolutionStatus) {
  if (!r) return null;
  if (r === "resolved")
    return (
      <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded border border-success-500/30 bg-success-500/10 text-success-500">
        resolved
      </span>
    );
  if (r === "unresolved")
    return (
      <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded border border-danger-500/30 bg-danger-500/10 text-danger-500">
        unresolved
      </span>
    );
  return (
    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded border border-warn-500/30 bg-warn-500/10 text-warn-500">
      partial
    </span>
  );
}

export default function CallsPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: calls, error, isLoading } = useSWR(["calls", activeTenantId], () => api.calls(100, activeTenantId));

  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("all");

  const filteredCalls = useMemo(() => {
    if (!calls) return [];
    let result = calls;

    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter((c) =>
        (c.caller_name || "").toLowerCase().includes(q) ||
        (c.caller_phone || "").includes(q) ||
        c.id.toLowerCase().includes(q) ||
        (c.intent || "").toLowerCase().includes(q)
      );
    }

    if (filterStatus !== "all") {
      result = result.filter((c) => c.outcome === filterStatus);
    }

    return result.sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());
  }, [calls, search, filterStatus]);

  const columns = [
    {
      key: "id",
      label: "ID",
      render: (c: Call) => (
        <button onClick={() => navigator.clipboard?.writeText(c.id)} title="Copy ID" className="font-mono text-[#ff2d78] font-bold text-xs hover:underline underline-offset-2">#{c.id.slice(0, 8)}</button>
      ),
    },
    {
      key: "caller",
      label: "Participant",
      render: (c: Call) => (
        <div>
          <div className="text-sm font-medium text-[#e8e0f0]">{c.caller_name || "Regional Agent"}</div>
          <div className="text-[10px] font-mono text-[#a098b0]">{c.caller_phone}</div>
        </div>
      ),
    },
    {
      key: "type",
      label: "Type",
      render: (c: Call) => (
        <span className="text-[10px] font-mono uppercase tracking-wider text-[#a098b0] px-2 py-0.5 rounded border border-[#302840]/40 bg-[#1e1e30]/30">
          {c.intent || "Order Verification"}
        </span>
      ),
    },
    {
      key: "status",
      label: "Status",
      render: (c: Call) => (
        <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${statusBg(c.outcome)} ${statusColor(c.outcome)}`}>
          {c.outcome}
        </span>
      ),
    },
    {
      key: "resolution",
      label: "Resolution",
      render: (c: Call) => resolutionBadge(c.resolution_status),
    },
    {
      key: "satisfaction",
      label: "Satisfaction",
      render: (c: Call) => satisfactionBadge(c.satisfaction),
    },
    {
      key: "time",
      label: "Time",
      render: (c: Call) => (
        <span className="text-xs text-[#a098b0] font-mono">{fmtRelative(c.started_at)}</span>
      ),
    },
    {
      key: "duration",
      label: "Duration",
      render: (c: Call) => (
        <span className="text-xs text-[#a098b0] font-mono">{fmtDuration(c.duration_sec)}</span>
      ),
    },
  ];

  return (
    <div className="space-y-5">
      <SectionCard className="no-pad" title="Call Logs & Transcripts" subtitle={`${activeTenant.name} · ${calls?.length ?? 0} calls`} icon={<PhoneCall size={16} className="text-[#ff2d78]" />}
        action={
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#a098b0]" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search calls..."
                className="pl-9 pr-4 py-2 rounded-lg bg-[#0a0a12] border border-[#302840] text-xs text-[#e8e0f0] placeholder-[#5a5068] focus:outline-none focus:border-[#ff2d78]/50 w-48"
              />
            </div>
            <div className="relative">
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
                className="appearance-none bg-[#0a0a12] border border-[#302840] text-xs text-[#e8e0f0] rounded-lg px-3 py-2 pr-8 focus:outline-none focus:border-[#ff2d78]/50"
              >
                <option value="all">All Status</option>
                <option value="completed">Completed</option>
                <option value="in_progress">In Progress</option>
                <option value="abandoned">Abandoned</option>
              </select>
              <ChevronDown size={12} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#a098b0] pointer-events-none" />
            </div>
          </div>
        }
      >
        {isLoading && (
          <div className="text-center text-[#a098b0] py-12 text-sm">Loading calls...</div>
        )}
        {error && (
          <div className="rounded border border-danger-500/30 bg-danger-500/10 p-3 text-sm text-danger-500">Failed to load calls. Is the API running?</div>
        )}
        {!isLoading && !error && (
          <DataTable
            columns={columns}
            data={filteredCalls}
            keyExtractor={(c) => c.id}
            loading={isLoading}
            emptyState={
              <div className="px-4 py-12 text-center">
                <PhoneCall size={32} className="mx-auto text-[#5a5068] mb-3" />
                <div className="text-sm text-[#a098b0]">No calls logged yet.</div>
                <div className="text-xs text-[#5a5068] mt-1">Use the phone simulator to start an interactive call.</div>
              </div>
            }
          />
        )}
      </SectionCard>
    </div>
  );
}
