"use client";

import { useState, useMemo, useEffect } from "react";
import useSWR from "swr";
import {
  PhoneCall,
  ShieldCheck,
  ShieldOff,
  AlertCircle,
  Radio,
  Volume2,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Download,
  Calendar,
  Layers,
} from "lucide-react";
import { api } from "@/lib/api";
import { fmtRelative, fmtDuration } from "@/lib/format";
import { useTenant } from "@/lib/tenant-context";
import type { Call, CallTurn, CallAction, ResolutionStatus, Satisfaction } from "@/lib/types";

// Elapsed timer that updates every second client-side
function useElapsed(startedAt: number) {
  const [elapsed, setElapsed] = useState(Math.round(Date.now() / 1000 - startedAt));
  useEffect(() => {
    const id = setInterval(() => setElapsed(Math.round(Date.now() / 1000 - startedAt)), 1000);
    return () => clearInterval(id);
  }, [startedAt]);
  return elapsed;
}

function ActiveCallCard({ c }: { c: any }) {
  const elapsed = useElapsed(c.started_at);
  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;
  return (
    <div className="rounded-xl border border-[#00ffcc]/30 bg-[#00ffcc]/10 p-4 flex items-center justify-between gap-4 shadow-sm">
      <div className="flex items-center gap-3">
        <span className="relative flex h-3 w-3 shrink-0">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00ffcc] opacity-75" />
          <span className="relative inline-flex rounded-full h-3 w-3 bg-[#00ffcc]" />
        </span>
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-white">
              {c.caller_name || c.caller_phone || "Live Inbound Call"}
            </span>
            <span className="text-xs font-mono text-[#94a3b8]">{c.caller_phone}</span>
          </div>
          <p className="text-xs text-[#00ffcc] font-mono mt-0.5">
            Agent handling turn • Intent: {c.intent || "Order Processing"}
          </p>
        </div>
      </div>
      <div className="text-right">
        <div className="text-base font-mono font-bold text-[#00ffcc]">
          {String(mins).padStart(2, "0")}:{String(secs).padStart(2, "0")}
        </div>
        <span className="text-[10px] font-mono text-[#94a3b8] uppercase">In Progress</span>
      </div>
    </div>
  );
}

export default function CallsPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: calls, error, isLoading } = useSWR(["calls", activeTenantId], () => api.calls(100, activeTenantId));
  const { data: activeCalls } = useSWR(
    ["active-calls", activeTenantId],
    () => api.activeCalls(activeTenantId),
    { refreshInterval: 5000 },
  );

  const [searchQuery, setSearchQuery] = useState("");
  const [filterTab, setFilterTab] = useState<"all" | "completed" | "escalated" | "orders">("all");
  const [expandedTranscripts, setExpandedTranscripts] = useState<Record<string, boolean>>({});

  const toggleExpand = (id: string) => {
    setExpandedTranscripts((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const filteredCalls = useMemo(() => {
    const list = (calls as Call[]) || [];
    return list.filter((c) => {
      const matchTab =
        filterTab === "all" ? true :
        filterTab === "completed" ? (c.outcome === "completed" || c.resolution_status === "resolved") :
        filterTab === "escalated" ? (c.escalated || c.outcome === "escalated") :
        (c.intent && c.intent.toLowerCase().includes("order"));

      const q = searchQuery.toLowerCase().trim();
      const matchSearch = !q ||
        c.id.toLowerCase().includes(q) ||
        (c.caller_name && c.caller_name.toLowerCase().includes(q)) ||
        (c.caller_phone && c.caller_phone.includes(q)) ||
        (c.intent && c.intent.toLowerCase().includes(q)) ||
        (c.reason && c.reason.toLowerCase().includes(q));

      return matchTab && matchSearch;
    });
  }, [calls, filterTab, searchQuery]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* ==================== PAGE HEADER ==================== */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#12121e] p-6 rounded-2xl border border-[#242436] shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-mono text-[#94a3b8]">
            <span>Telephony Records</span>
            <span>/</span>
            <span className="text-[#00ffcc] font-bold">{activeTenant.name}</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-headline font-bold text-white tracking-tight">
            Call Logs, Transcripts & Audio Inspector
          </h1>
          <p className="text-xs sm:text-sm text-[#94a3b8]">
            Complete multi-channel voice conversation records, caller verification, and audio playback.
          </p>
        </div>

        <button
          onClick={() => window.open("/api/calls/export", "_blank")}
          className="flex items-center gap-2 bg-[#181826] hover:bg-[#202034] text-[#cbd5e1] hover:text-white px-4 py-2 rounded-xl text-xs font-medium border border-[#2c2c40] transition-colors"
        >
          <Download size={14} />
          <span>Export All CSV</span>
        </button>
      </header>

      {/* ── Active Live Calls ── */}
      {activeCalls && activeCalls.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Radio size={14} className="text-[#00ffcc]" />
            <span className="text-xs font-mono font-bold uppercase text-[#00ffcc]">
              {activeCalls.length} Active Call{activeCalls.length > 1 ? "s" : ""} in Progress
            </span>
          </div>
          <div className="grid grid-cols-1 gap-3">
            {activeCalls.map((c: any) => (
              <ActiveCallCard key={c.call_id} c={c} />
            ))}
          </div>
        </div>
      )}

      {/* ── Controls Bar ── */}
      <div className="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-3 bg-[#141422] p-3 rounded-2xl border border-[#28283c]">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#64748b]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by caller name, phone, PO ID, or transcript keywords..."
            className="w-full bg-[#10101a] border border-[#28283c] rounded-xl pl-9 pr-4 py-2 text-xs text-white focus:outline-none focus:border-[#ff2d78]"
          />
        </div>

        <div className="flex items-center bg-[#10101a] p-1 rounded-xl border border-[#28283c] shrink-0">
          {(["all", "completed", "escalated", "orders"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setFilterTab(tab)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors ${
                filterTab === tab ? "bg-[#ff2d78] text-white" : "text-[#94a3b8] hover:text-white"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* ── Call Records List ── */}
      <div className="space-y-4">
        {isLoading && (
          <div className="text-center text-xs text-[#94a3b8] py-12">
            Loading call logs...
          </div>
        )}
        {error && (
          <div className="p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-xs text-red-400">
            Failed to load call logs. Please verify backend API connectivity.
          </div>
        )}

        {filteredCalls.map((c) => {
          const isExpanded = expandedTranscripts[c.id] ?? true;
          return (
            <div key={c.id} className="bg-[#141422] border border-[#28283c] rounded-2xl p-5 shadow-sm space-y-4">
              {/* Header row */}
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-3 border-b border-[#242436]">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-9 h-9 rounded-xl flex items-center justify-center font-mono font-bold text-xs ${
                      c.language === "hi"
                        ? "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                        : "bg-[#00ffcc]/15 text-[#00ffcc] border border-[#00ffcc]/30"
                    }`}
                  >
                    {c.language ? c.language.toUpperCase() : "HI"}
                  </div>
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-headline font-bold text-sm text-white">
                        {c.caller_name || "Regional Supplier Contact"}
                      </span>
                      <span className="text-xs font-mono text-[#ff2d78]">#{c.id.slice(0, 10)}</span>
                      {c.verified ? (
                        <span className="flex items-center gap-1 text-[10px] font-mono text-[#00ffcc] bg-[#00ffcc]/10 px-2 py-0.5 rounded border border-[#00ffcc]/30">
                          <ShieldCheck size={11} /> PIN Verified
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-[10px] font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30">
                          <ShieldOff size={11} /> Unverified
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] font-mono text-[#94a3b8] mt-0.5">
                      {fmtRelative(c.started_at)} • Duration: {fmtDuration(c.duration_sec)} • Phone: {c.caller_phone || "Inbound Telephony"}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`px-2.5 py-1 rounded-md text-[10px] font-mono font-bold uppercase ${
                      c.outcome === "completed" || c.resolution_status === "resolved"
                        ? "bg-[#00ffcc]/15 text-[#00ffcc] border border-[#00ffcc]/30"
                        : c.escalated || c.outcome === "escalated"
                        ? "bg-red-500/15 text-red-400 border border-red-500/30"
                        : "bg-blue-500/15 text-blue-400 border border-blue-500/30"
                    }`}
                  >
                    {c.outcome || "COMPLETED"}
                  </span>

                  <button
                    onClick={() => toggleExpand(c.id)}
                    className="p-1.5 text-[#94a3b8] hover:text-white hover:bg-[#181826] rounded-lg transition-colors"
                    title={isExpanded ? "Collapse Transcript" : "Expand Transcript"}
                  >
                    {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </button>
                </div>
              </div>

              {/* Summary / Reasoning box */}
              {(c.reason || c.solution || c.summary) && (
                <div className="bg-[#181826] p-3.5 rounded-xl border border-[#28283c] text-xs text-[#cbd5e1] space-y-1">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-[#94a3b8] font-bold block">
                    Operational Summary
                  </span>
                  <p>{c.summary || c.solution || c.reason}</p>
                </div>
              )}

              {/* Recording Player */}
              {c.recording_url && (
                <div className="p-3 bg-[#10101a] rounded-xl border border-[#28283c] flex items-center gap-3">
                  <div className="flex items-center gap-1.5 text-xs font-mono text-[#00ffcc] shrink-0">
                    <Volume2 size={14} /> Call Audio
                  </div>
                  <audio controls src={c.recording_url} className="h-8 w-full max-w-md accent-[#ff2d78]" preload="none" />
                </div>
              )}

              {/* Transcript Drawer */}
              {isExpanded && c.transcript && c.transcript.length > 0 && (
                <div className="space-y-2 bg-[#10101a] p-4 rounded-xl border border-[#28283c]">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-[#94a3b8] font-bold block pb-1 border-b border-[#242436]">
                    Full Turn-by-Turn Transcript
                  </span>
                  <div className="space-y-2 max-h-60 overflow-y-auto pt-1">
                    {(c.transcript as CallTurn[]).map((t, i) => (
                      <div key={i} className="text-xs leading-relaxed">
                        <span
                          className={`font-mono text-[10px] font-bold uppercase mr-2 ${
                            t.role === "agent" ? "text-[#ff2d78]" : "text-[#00ffcc]"
                          }`}
                        >
                          {t.role === "agent" ? (activeTenant.agent_name || "Vaani") : "Caller"}:
                        </span>
                        <span className="text-[#f1f5f9]">{t.text}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {!isLoading && filteredCalls.length === 0 && (
          <div className="bg-[#141422] border border-dashed border-[#28283c] rounded-2xl p-12 text-center space-y-3">
            <PhoneCall className="mx-auto text-[#64748b]" size={32} />
            <p className="text-sm font-headline font-bold text-white">
              No matching call records found
            </p>
            <p className="text-xs text-[#94a3b8]">
              Place a call via Phone Simulator or Twilio phone number to record interactions.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
