"use client";

import { useState, useEffect } from "react";
import useSWR from "swr";
import { PhoneCall, ShieldCheck, ShieldOff, AlertCircle, Radio } from "lucide-react";
import { api } from "@/lib/api";
import { fmtRelative, fmtDuration, statusBg, statusColor } from "@/lib/format";
import { useTenant } from "@/lib/tenant-context";
import type { Call, CallTurn, CallAction, ResolutionStatus, Satisfaction } from "@/lib/types";

// ── Badge helpers ─────────────────────────────────────────────────────────────

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
  // neutral
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
  // partial
  return (
    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded border border-warn-500/30 bg-warn-500/10 text-warn-500">
      partial
    </span>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

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
    <div className="rounded-lg border border-[#00ffcc]/30 bg-[#00ffcc]/5 p-4 flex items-center gap-3 flex-wrap">
      <span className="relative flex h-3 w-3 shrink-0">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00ffcc] opacity-60" />
        <span className="relative inline-flex rounded-full h-3 w-3 bg-[#00ffcc]" />
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold text-[#e8e0f0]">
            {c.caller_name || c.company_name || c.caller_phone || "Unknown Caller"}
          </span>
          {c.caller_name && c.caller_phone && (
            <span className="text-[11px] font-mono text-[#a098b0]">{c.caller_phone}</span>
          )}
          {c.verified ? (
            <span className="flex items-center gap-1 text-[10px] font-mono text-[#a098b0] border border-[#302840]/60 bg-[#1e1e30]/40 px-1.5 py-0.5 rounded">
              <ShieldCheck size={10} /> verified
            </span>
          ) : (
            <span className="flex items-center gap-1 text-[10px] font-mono text-warn-500 border border-warn-500/30 bg-warn-500/10 px-1.5 py-0.5 rounded">
              <ShieldOff size={10} /> unverified
            </span>
          )}
        </div>
        {c.intent && (
          <div className="text-[11px] font-mono text-[#a098b0] mt-0.5 truncate">
            Intent: {c.intent}
          </div>
        )}
      </div>
      <div className="text-right shrink-0">
        <div className="text-sm font-mono text-[#00ffcc]">
          {String(mins).padStart(2, "0")}:{String(secs).padStart(2, "0")}
        </div>
        <div className="text-[10px] font-mono text-[#5a5068]">{c.turn_count} turns</div>
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

  return (
    <>
      <div className="px-6 pt-6 pb-2 flex items-baseline gap-3">
        <h1 className="text-xl font-bold text-[#e8e0f0]">Call Logs & Transcripts</h1>
        <span className="text-xs text-[#a098b0]">{activeTenant.name} · {calls?.length ?? 0} calls</span>
      </div>

      {/* ── Live Active Calls ── */}
      {activeCalls && activeCalls.length > 0 && (
        <div className="px-6 pb-2">
          <div className="flex items-center gap-2 mb-2">
            <Radio size={13} className="text-[#00ffcc]" />
            <span className="text-xs font-mono uppercase tracking-wider text-[#00ffcc]">
              {activeCalls.length} call{activeCalls.length !== 1 ? "s" : ""} in progress
            </span>
          </div>
          <div className="space-y-2">
            {activeCalls.map((c: any) => (
              <ActiveCallCard key={c.call_id} c={c} />
            ))}
          </div>
        </div>
      )}

      <div className="p-6 space-y-3">
        {isLoading && <div className="text-center text-[#a098b0] py-12 text-sm">Loading calls...</div>}
        {error && <div className="rounded border border-danger-500/30 bg-danger-500/10 p-3 text-sm text-danger-500">Failed to load calls. Is the API running?</div>}
        {(calls as Call[])?.map((c) => (
          <div key={c.id} className="rounded-lg border border-[#302840]/60 bg-[#0f0f1a]/40 p-4">
            {/* ── Header row ── */}
            <div className="flex items-center gap-3 mb-3 flex-wrap">
              <div className={`h-9 w-9 rounded-full grid place-items-center text-[10px] font-mono shrink-0 ${
                c.language === "hi" ? "bg-amber-500/10 text-amber-400" : "bg-[#00ffcc]/10 text-[#00ffcc]"
              }`}>
                {c.language.toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm text-[#e8e0f0]">{c.caller_name || c.caller_phone || "Unknown Caller"}</span>
                  {/* Unverified caller warning */}
                  {!c.verified && (
                    <span className="flex items-center gap-1 text-[10px] font-mono text-warn-500 border border-warn-500/30 bg-warn-500/10 px-1.5 py-0.5 rounded" title="Caller identity not verified">
                      <ShieldOff size={10} /> unverified
                    </span>
                  )}
                  {c.verified && (
                    <span className="flex items-center gap-1 text-[10px] font-mono text-[#a098b0] border border-[#302840]/60 bg-[#1e1e30]/40 px-1.5 py-0.5 rounded" title="Caller verified">
                      <ShieldCheck size={10} /> verified
                    </span>
                  )}
                </div>
                <div className="text-[11px] font-mono text-[#a098b0]">
                  {fmtRelative(c.started_at)} · {fmtDuration(c.duration_sec)} · {c.caller_phone}
                </div>
              </div>
              {/* Outcome badge */}
              <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${statusBg(c.outcome)} ${statusColor(c.outcome)}`}>
                {c.outcome}
              </span>
              {/* Resolution status badge */}
              {resolutionBadge(c.resolution_status)}
              {/* Satisfaction badge */}
              {satisfactionBadge(c.satisfaction)}
              {/* Escalated badge */}
              {c.escalated && (
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded border border-danger-500/30 bg-danger-500/10 text-danger-500">
                  escalated
                </span>
              )}
              {/* Follow-up indicator */}
              {c.follow_up_required && (
                <span className="flex items-center gap-1 text-[10px] font-mono text-warn-500 border border-warn-500/30 bg-warn-500/10 px-1.5 py-0.5 rounded" title="Follow-up required">
                  <AlertCircle size={10} /> follow-up
                </span>
              )}
            </div>

            {/* ── Reason / Solution summary ── */}
            {(c.reason || c.solution) && (
              <div className="mb-3 rounded-md bg-[#141422]/60 border border-[#302840]/60 p-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
                {c.reason && (
                  <div>
                    <div className="text-[10px] font-mono uppercase tracking-wider text-[#a098b0] mb-1">Reason</div>
                    <div className="text-xs text-[#e8e0f0] leading-relaxed">{c.reason}</div>
                  </div>
                )}
                {c.solution && (
                  <div>
                    <div className="text-[10px] font-mono uppercase tracking-wider text-[#a098b0] mb-1">Solution</div>
                    <div className="text-xs text-[#e8e0f0] leading-relaxed">{c.solution}</div>
                  </div>
                )}
              </div>
            )}

            {/* ── Transcript ── */}
            {c.transcript && c.transcript.length > 0 && (
              <div className="rounded-md bg-[#07070f]/40 border border-[#302840]/60 p-3 space-y-2 max-h-72 overflow-y-auto font-sans">
                {(c.transcript as CallTurn[]).map((t, i) => (
                  <div key={i} className={`text-xs leading-relaxed ${t.role === "agent" ? "text-[#00ffcc]" : "text-[#e8e0f0]"}`}>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-[#a098b0] mr-2">
                      {t.role === "agent" ? "Vaani" : "Caller"}
                    </span>
                    {t.text}
                  </div>
                ))}
              </div>
            )}

            {/* ── Actions ── */}
            {c.actions && c.actions.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {(c.actions as CallAction[]).map((a, i) => (
                  <span key={i} className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#00ffcc]/10 text-[#00ffcc] border border-[#00ffcc]/20">
                    {a.name}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        {!isLoading && !error && (!calls || calls.length === 0) && (
          <div className="rounded-lg border border-dashed border-[#302840]/60 p-12 text-center">
            <PhoneCall className="mx-auto mb-3 text-[#5a5068]" />
            <div className="text-sm text-[#a098b0]">No calls logged yet for {activeTenant.name}.</div>
            <div className="text-xs text-[#5a5068] mt-1">Use the phone simulator to start an interactive call.</div>
          </div>
        )}
      </div>
    </>
  );
}
