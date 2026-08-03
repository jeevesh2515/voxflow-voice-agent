"use client";

import useSWR from "swr";
import { PhoneCall, ShieldCheck, ShieldOff, AlertCircle } from "lucide-react";
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

export default function CallsPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: calls, error, isLoading } = useSWR(["calls", activeTenantId], () => api.calls(100, activeTenantId));

  return (
    <>
      <div className="px-6 pt-6 pb-2 flex items-baseline gap-3">
        <h1 className="text-xl font-bold text-[#e8e0f0]">Call Logs & Transcripts</h1>
        <span className="text-xs text-[#a098b0]">{activeTenant.name} · {calls?.length ?? 0} calls</span>
      </div>
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
