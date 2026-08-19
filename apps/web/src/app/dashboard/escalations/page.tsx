"use client";

import { useState } from "react";
import useSWR, { mutate } from "swr";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  ShieldCheck,
  ShieldOff,
  UserCheck,
  Search,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import { api } from "@/lib/api";
import { fmtRelative, fmtTime } from "@/lib/format";
import { useTenant } from "@/lib/tenant-context";
import type { Call, Satisfaction } from "@/lib/types";

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
      className={`rounded-2xl border p-5 transition-all shadow-sm space-y-4 ${
        isResolved
          ? "border-[#28283c] bg-[#141422]/60 opacity-75"
          : "border-amber-500/30 bg-[#141422]"
      }`}
    >
      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 pb-3 border-b border-[#242436]">
        <div className="flex items-center gap-3">
          <div
            className={`w-9 h-9 rounded-xl flex items-center justify-center font-mono font-bold text-xs ${
              isResolved
                ? "bg-[#00ffcc]/15 text-[#00ffcc] border border-[#00ffcc]/30"
                : "bg-amber-500/15 text-amber-400 border border-amber-500/30"
            }`}
          >
            {isResolved ? "OK" : "REQ"}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-headline font-bold text-sm text-white">
                {call.caller_name || call.caller_phone || "Regional Contact"}
              </span>
              <span className="text-xs font-mono text-[#ff2d78]">#{call.id.slice(0, 10)}</span>
              {call.verified ? (
                <span className="flex items-center gap-1 text-[10px] font-mono text-[#00ffcc] bg-[#00ffcc]/10 px-2 py-0.5 rounded border border-[#00ffcc]/30">
                  <ShieldCheck size={11} /> PIN Verified
                </span>
              ) : (
                <span className="flex items-center gap-1 text-[10px] font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30">
                  <ShieldOff size={11} /> Unverified
                </span>
              )}
            </div>
            <div className="text-[11px] font-mono text-[#94a3b8] mt-0.5 flex items-center gap-2">
              <Clock size={11} />
              <span>{fmtRelative(call.started_at)}</span>
              <span>•</span>
              <span>Phone: {call.caller_phone || "Inbound Telephony"}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {call.escalated && (
            <span className="text-[10px] font-mono uppercase px-2.5 py-1 rounded-md border border-red-500/30 bg-red-500/15 text-red-400 font-bold">
              Escalated
            </span>
          )}
          {isResolved && (
            <span className="flex items-center gap-1 text-[10px] font-mono uppercase px-2.5 py-1 rounded-md border border-[#00ffcc]/30 bg-[#00ffcc]/15 text-[#00ffcc] font-bold">
              <CheckCircle2 size={12} /> Staff Resolved
            </span>
          )}
        </div>
      </div>

      {/* ── Summary & Reasoning ── */}
      {(call.reason || call.solution || call.summary) && (
        <div className="bg-[#181826] p-4 rounded-xl border border-[#28283c] text-xs text-[#cbd5e1] space-y-1">
          <span className="text-[10px] font-mono uppercase tracking-wider text-[#94a3b8] font-bold block">
            Escalation Reason / Notes
          </span>
          <p>{call.summary || call.reason || call.solution}</p>
        </div>
      )}

      {/* ── Existing Staff Note ── */}
      {isResolved && call.staff_resolution && (
        <div className="p-3.5 rounded-xl bg-[#00ffcc]/5 border border-[#00ffcc]/20 text-xs">
          <div className="text-[10px] font-mono uppercase tracking-wider text-[#00ffcc] font-bold mb-1 flex items-center gap-1.5">
            <UserCheck size={12} />
            <span>Staff Action Record</span>
            {call.staff_resolved_at && (
              <span className="text-[#94a3b8] font-normal">
                • {fmtTime(call.staff_resolved_at)}
              </span>
            )}
          </div>
          <p className="text-[#f1f5f9]">{call.staff_resolution}</p>
        </div>
      )}

      {/* ── Staff Resolution Input ── */}
      <div className="space-y-2 pt-1">
        <label className="block text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] font-bold">
          {isResolved ? "Update Staff Follow-up Note" : "Submit Staff Resolution"}
        </label>
        <textarea
          rows={2}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Enter staff resolution details (e.g. 'Confirmed with supplier over WhatsApp, order approved')..."
          className="w-full rounded-xl border border-[#28283c] bg-[#10101a] px-3.5 py-2 text-xs text-white placeholder:text-[#64748b] font-body focus:outline-none focus:border-[#ff2d78]"
        />
        {saveError && (
          <div className="text-xs text-red-400 font-mono">{saveError}</div>
        )}
        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving || !draft.trim()}
            className="px-4 py-1.5 rounded-xl bg-[#ff2d78] hover:bg-[#e02669] text-white text-xs font-bold transition-colors disabled:opacity-40 shadow-sm"
          >
            {saving ? "Saving..." : isResolved ? "Update Note" : "Mark as Resolved"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function EscalationsPage() {
  const { activeTenantId, activeTenant } = useTenant();

  const swrKey = ["escalations", activeTenantId];
  const { data: rawCalls, error, isLoading } = useSWR(swrKey, () =>
    api.escalations(activeTenantId),
  );

  const calls = (rawCalls as Call[] | undefined)?.filter(
    (c) => c.escalated || c.follow_up_required,
  );

  const pendingCount = calls?.filter((c) => !c.staff_resolved_at).length ?? 0;

  function refreshAll() {
    mutate(swrKey);
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* ==================== PAGE HEADER ==================== */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#12121e] p-6 rounded-2xl border border-[#242436] shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-mono text-[#94a3b8]">
            <span>Human Handoff</span>
            <span>/</span>
            <span className="text-[#00ffcc] font-bold">{activeTenant.name}</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-headline font-bold text-white tracking-tight">
            Escalations & Staff Resolution Queue
          </h1>
          <p className="text-xs sm:text-sm text-[#94a3b8]">
            Calls flagged by AI for human supervisor inspection, manual PIN verification, and staff follow-ups.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-3.5 py-1.5 rounded-xl font-mono text-xs font-bold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            {pendingCount} Pending Review
          </span>
        </div>
      </header>

      {/* ── Escalation Items List ── */}
      <div className="space-y-4">
        {isLoading && (
          <div className="text-center text-xs text-[#94a3b8] py-12">
            Loading escalation items...
          </div>
        )}
        {error && (
          <div className="p-4 rounded-xl border border-red-500/30 bg-red-500/10 text-xs text-red-400">
            Failed to load escalation items. Please check API status.
          </div>
        )}

        {calls?.map((c) => (
          <EscalationCard key={c.id} call={c} onSaved={refreshAll} />
        ))}

        {!isLoading && !error && calls !== undefined && calls.length === 0 && (
          <div className="bg-[#141422] border border-dashed border-[#28283c] rounded-2xl p-12 text-center space-y-3">
            <CheckCircle2 className="mx-auto text-[#00ffcc]" size={32} />
            <p className="text-sm font-headline font-bold text-white">
              Zero pending escalations for {activeTenant.name}
            </p>
            <p className="text-xs text-[#94a3b8]">
              All incoming caller inquiries have been autonomously handled by the AI voice agent.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
