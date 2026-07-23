"use client";

import useSWR from "swr";
import { PhoneCall } from "lucide-react";
import Topbar from "@/components/Topbar";
import { api } from "@/lib/api";
import { fmtRelative, fmtDuration, statusBg, statusColor } from "@/lib/format";
import { useTenant } from "@/lib/tenant-context";
import type { Call, CallTurn, CallAction } from "@/lib/types";

export default function CallsPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: calls, error, isLoading } = useSWR(["calls", activeTenantId], () => api.calls(100, activeTenantId));

  return (
    <>
      <Topbar title="Call Logs & Transcripts" subtitle={`${activeTenant.name} · ${calls?.length ?? 0} calls`} />
      <div className="p-6 space-y-3">
        {isLoading && <div className="text-center text-ink-400 py-12 text-sm">Loading calls...</div>}
        {error && <div className="rounded border border-danger-500/30 bg-danger-500/10 p-3 text-sm text-danger-400">Failed to load calls. Is the API running?</div>}
        {(calls as Call[])?.map((c) => (
          <div key={c.id} className="rounded-lg border border-ink-700/60 bg-ink-900/40 p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className={`h-9 w-9 rounded-full grid place-items-center text-[10px] font-mono ${
                c.language === "hi" ? "bg-amber-500/10 text-amber-400" : "bg-vox-500/10 text-vox-300"
              }`}>
                {c.language.toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm text-ink-50">{c.caller_name || c.caller_phone || "Unknown Caller"}</div>
                <div className="text-[11px] font-mono text-ink-400">
                  {fmtRelative(c.started_at)} · {fmtDuration(c.duration_sec)} · {c.caller_phone}
                </div>
              </div>
              <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${statusBg(c.outcome)} ${statusColor(c.outcome)}`}>
                {c.outcome}
              </span>
              {c.escalated && (
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded border border-danger-500/30 bg-danger-500/10 text-danger-500">
                  escalated
                </span>
              )}
            </div>

            {c.transcript && c.transcript.length > 0 && (
              <div className="rounded-md bg-ink-950/40 border border-ink-800/60 p-3 space-y-2 max-h-72 overflow-y-auto font-sans">
                {(c.transcript as CallTurn[]).map((t, i) => (
                  <div key={i} className={`text-xs leading-relaxed ${t.role === "agent" ? "text-vox-300" : "text-ink-100"}`}>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-ink-500 mr-2">
                      {t.role === "agent" ? "Vaani" : "Caller"}
                    </span>
                    {t.text}
                  </div>
                ))}
              </div>
            )}

            {c.actions && c.actions.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {(c.actions as CallAction[]).map((a, i) => (
                  <span key={i} className="text-[10px] font-mono px-2 py-0.5 rounded bg-vox-500/10 text-vox-300 border border-vox-500/20">
                    {a.name}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        {!isLoading && !error && (!calls || calls.length === 0) && (
          <div className="rounded-lg border border-dashed border-ink-700/60 p-12 text-center">
            <PhoneCall className="mx-auto mb-3 text-ink-600" />
            <div className="text-sm text-ink-300">No calls logged yet for {activeTenant.name}.</div>
            <div className="text-xs text-ink-500 mt-1">Use the phone simulator to start an interactive call.</div>
          </div>
        )}
      </div>
    </>
  );
}
