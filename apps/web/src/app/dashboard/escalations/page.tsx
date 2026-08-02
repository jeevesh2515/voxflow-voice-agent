"use client";

import { useState } from "react";
import useSWR, { mutate } from "swr";
import { AlertTriangle, CheckCircle2, Clock, ShieldCheck, ShieldOff } from "lucide-react";
import { api } from "@/lib/api";
import { fmtRelative, fmtTime } from "@/lib/format";
import { useTenant } from "@/lib/tenant-context";
import type { Call, Satisfaction } from "@/lib/types";

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
  return (
    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded border border-[#5a5068]/60 bg-[#1e1e30]/60 text-[#a098b0]">
      neutral
    </span>
  );
}

// ── Single escalation card ────────────────────────────────────────────────────

function EscalationCard({ call, onSaved }: { call: Call; onSaved: () => void }) {
  const [draft, setDraft] = useState(call.staff_resolution ?? "");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const isResolved = Boolean(call.staff_resolved_at);

  async function handleSave() {
    if (!draft.trim()) return;
    setSaving(true);
    setSaveError(null);
    try {
      await api.patchResolution(call.id, draft.trim());
      onSaved();
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Failed to save.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      className={`rounded-lg border p-4 transition-opacity ${
        isResolved
          ? "border-[#302840]/40 bg-[#0f0f1a]/20 opacity-60"
          : "border-[#302840]/60 bg-[#0f0f1a]/40"
      }`}
    >
      {/* ── Header ── */}
      <div className="flex items-start gap-3 mb-3 flex-wrap">
        <div className={`h-9 w-9 rounded-full grid place-items-center text-[10px] font-mono shrink-0 ${
          call.language === "hi" ? "bg-amber-500/10 text-amber-400" : "bg-[#00ffcc]/10 text-[#00ffcc]"
        }`}>
          {call.language.toUpperCase()}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-[#e8e0f0]">
              {call.caller_name || call.caller_phone || "Unknown Caller"}
            </span>
            {call.caller_name && (
              <span className="text-[11px] font-mono text-[#a098b0]">{call.caller_phone}</span>
            )}
            {call.verified ? (
              <span className="flex items-center gap-1 text-[10px] font-mono text-[#a098b0] border border-[#302840]/60 bg-[#1e1e30]/40 px-1.5 py-0.5 rounded">
                <ShieldCheck size={10} /> verified
              </span>
            ) : (
              <span className="flex items-center gap-1 text-[10px] font-mono text-warn-500 border border-warn-500/30 bg-warn-500/10 px-1.5 py-0.5 rounded">
                <ShieldOff size={10} /> unverified
              </span>
            )}
          </div>
          <div className="text-[11px] font-mono text-[#a098b0] mt-0.5 flex items-center gap-2">
            <Clock size={10} />
            {fmtRelative(call.started_at)}
            <span className="text-[#5a5068]">·</span>
            {fmtTime(call.started_at)}
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {call.escalated && (
            <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded border border-danger-500/30 bg-danger-500/10 text-danger-500">
              escalated
            </span>
          )}
          {call.follow_up_required && !call.escalated && (
            <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded border border-warn-500/30 bg-warn-500/10 text-warn-500">
              follow-up
            </span>
          )}
          {satisfactionBadge(call.satisfaction)}
          {isResolved && (
            <span className="flex items-center gap-1 text-[10px] font-mono uppercase px-2 py-0.5 rounded border border-success-500/30 bg-success-500/10 text-success-500">
              <CheckCircle2 size={10} /> staff resolved
            </span>
          )}
        </div>
      </div>

      {/* ── Reason / Solution ── */}
      {(call.reason || call.solution) && (
        <div className="mb-3 rounded-md bg-[#141422]/60 border border-[#302840]/60 p-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
          {call.reason && (
            <div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-[#a098b0] mb-1">Reason</div>
              <div className="text-xs text-[#e8e0f0] leading-relaxed">{call.reason}</div>
            </div>
          )}
          {call.solution && (
            <div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-[#a098b0] mb-1">Agent solution</div>
              <div className="text-xs text-[#e8e0f0] leading-relaxed">{call.solution}</div>
            </div>
          )}
        </div>
      )}

      {/* ── Existing staff resolution ── */}
      {isResolved && call.staff_resolution && (
        <div className="mb-3 rounded-md bg-success-500/5 border border-success-500/20 p-3">
          <div className="text-[10px] font-mono uppercase tracking-wider text-success-500 mb-1">
            Staff Resolution
            {call.staff_resolved_at && (
              <span className="ml-2 text-[#a098b0] normal-case tracking-normal">
                · {fmtTime(call.staff_resolved_at)}
              </span>
            )}
          </div>
          <div className="text-xs text-[#e8e0f0] leading-relaxed">{call.staff_resolution}</div>
        </div>
      )}

      {/* ── Resolution textarea + save ── */}
      <div className="space-y-2">
        <label className="block text-[10px] font-mono uppercase tracking-wider text-[#a098b0]">
          {isResolved ? "Update Staff Resolution" : "Add Staff Resolution"}
        </label>
        <textarea
          rows={3}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Describe the follow-up action taken or outcome..."
          className="w-full rounded border border-[#302840]/60 bg-[#141422]/60 px-3 py-2 text-xs text-[#e8e0f0] placeholder-[#5a5068] font-mono resize-y focus:outline-none focus:border-[#ff2d78]/50 focus:bg-[#141422]"
        />
        {saveError && (
          <div className="text-xs text-danger-500 font-mono">{saveError}</div>
        )}
        <button
          onClick={handleSave}
          disabled={saving || !draft.trim()}
          className="px-4 py-1.5 rounded border border-[#ff2d78]/40 bg-[#ff2d78]/10 text-[#ff2d78] text-xs font-mono uppercase tracking-wider hover:bg-[#ff2d78]/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {saving ? "Saving…" : "Save Resolution"}
        </button>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function EscalationsPage() {
  const { activeTenantId, activeTenant } = useTenant();

  const swrKey = ["escalations", activeTenantId];
  const { data: rawCalls, error, isLoading } = useSWR(swrKey, () =>
    api.escalations(activeTenantId),
  );

  // Client-side filter: show calls where escalated OR follow_up_required
  const calls = (rawCalls as Call[] | undefined)?.filter(
    (c) => c.escalated || c.follow_up_required,
  );

  const pendingCount = calls?.filter((c) => !c.staff_resolved_at).length ?? 0;

  function refreshAll() {
    mutate(swrKey);
  }

  return (
    <>
      {/* ── Inline page header (no Topbar import — layout already renders it) ── */}
      <div className="px-6 pt-6 pb-2 flex items-baseline gap-3 flex-wrap">
        <AlertTriangle size={18} className="text-danger-500 self-center" />
        <h1 className="text-xl font-bold text-[#e8e0f0]">Escalations & Follow-ups</h1>
        <span className="text-xs text-[#a098b0]">
          {activeTenant.name}
          {calls !== undefined && (
            <>
              {" · "}
              <span className="text-danger-500">{pendingCount} pending</span>
              {" / "}
              {calls.length} total
            </>
          )}
        </span>
      </div>

      <div className="p-6 space-y-3">
        {isLoading && (
          <div className="text-center text-[#a098b0] py-12 text-sm">Loading escalations…</div>
        )}
        {error && (
          <div className="rounded border border-danger-500/30 bg-danger-500/10 p-3 text-sm text-danger-500">
            Failed to load calls. Is the API running?
          </div>
        )}

        {calls?.map((c) => (
          <EscalationCard key={c.id} call={c} onSaved={refreshAll} />
        ))}

        {!isLoading && !error && calls !== undefined && calls.length === 0 && (
          <div className="rounded-lg border border-dashed border-[#302840]/60 p-12 text-center">
            <CheckCircle2 className="mx-auto mb-3 text-success-500" size={24} />
            <div className="text-sm text-[#a098b0]">No escalations or pending follow-ups for {activeTenant.name}.</div>
            <div className="text-xs text-[#5a5068] mt-1">All calls resolved — great work.</div>
          </div>
        )}
      </div>
    </>
  );
}
