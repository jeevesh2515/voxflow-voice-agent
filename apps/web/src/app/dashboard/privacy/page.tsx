"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";
import { Database, Download, EyeOff, FileLock2, FileOutput, RotateCcw, ShieldCheck, Trash2, Play, History, Globe, Building2, Server, Smartphone, Brain } from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";

const TRANSCRIPT_OPTIONS = [7, 14, 30, 60, 90] as const;
const CALL_OPTIONS = [30, 60, 90, 180, 365] as const;

export default function PrivacyControlsPage() {
  const { activeTenant, activeTenantId, demoMode } = useTenant();
  const [retention, setRetention] = useState({ call_retention_days: 90, transcript_retention_days: 30, pii_masking_enabled: true, data_residency_region: "eu-west-2" });
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [showEraseModal, setShowEraseModal] = useState(false);
  const [confirmText, setConfirmText] = useState("");
  const [dryRun, setDryRun] = useState(true);

  const { data: retentionData, mutate: refreshRetention } = useSWR(
    activeTenantId ? ["privacy-retention", activeTenantId] : null,
    () => api.privacyRetention(activeTenantId),
  );
  // fallback to legacy overview for metrics
  const { data: overview } = useSWR(activeTenantId ? ["privacy-overview", activeTenantId] : null, () => api.privacyOverview(activeTenantId));
  const { data: resetPreview } = useSWR(activeTenantId ? ["privacy-reset-preview", activeTenantId] : null, () => api.demoResetPreview(activeTenantId));
  const { data: purgeLogs, mutate: refreshLogs } = useSWR(activeTenantId ? ["purge-logs", activeTenantId] : null, () => api.purgeLogs(activeTenantId));

  const canManage = !demoMode && activeTenant.role === "owner";
  const canExport = !demoMode && (activeTenant.role === "owner" || activeTenant.role === "operator");

  const { data: requestLedger } = useSWR(canManage && activeTenantId ? ["privacy-requests", activeTenantId] : null, () => api.privacyRequests(activeTenantId));

  useEffect(() => {
    if (retentionData?.retention) {
      setRetention({
        call_retention_days: retentionData.retention.call_retention_days,
        transcript_retention_days: retentionData.retention.transcript_retention_days,
        pii_masking_enabled: retentionData.retention.pii_masking_enabled,
        data_residency_region: retentionData.retention.data_residency_region,
      });
    }
  }, [retentionData]);

  async function saveRetention() {
    if (!canManage) return;
    setSaving(true); setActionError(null); setMessage(null);
    try {
      await api.updatePrivacyRetention(activeTenantId, {
        call_retention_days: retention.call_retention_days,
        transcript_retention_days: retention.transcript_retention_days,
        pii_masking_enabled: retention.pii_masking_enabled as any,
        data_residency_region: retention.data_residency_region,
      });
      await refreshRetention();
      setMessage("Retention policy saved.");
    } catch (e) { setActionError(e instanceof Error ? e.message : "Unable to save retention."); } finally { setSaving(false); }
  }

  async function handleExport() {
    if (!canExport || !subject.trim()) return;
    setSaving(true); setActionError(null); setMessage(null);
    try {
      const res = await api.dsarExport(activeTenantId, subject.trim());
      const blob = new Blob([JSON.stringify(res.export, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `dsar-${subject.trim().replace(/[^a-z0-9]/gi, "_")}.json`; a.click(); URL.revokeObjectURL(url);
      setMessage("DSAR export downloaded.");
    } catch (e) { setActionError(e instanceof Error ? e.message : "Export failed."); } finally { setSaving(false); }
  }

  async function handleErase() {
    if (!canManage || confirmText !== "DELETE DATA") return;
    setSaving(true); setActionError(null); setMessage(null);
    try {
      await api.eraseDataSubject(activeTenantId, { search_phone_or_email: subject.trim(), confirmation_token: "DELETE DATA" });
      setShowEraseModal(false); setConfirmText(""); setSubject("");
      await refreshLogs();
      setMessage("Caller personal data anonymized. Financial order refs preserved.");
    } catch (e) { setActionError(e instanceof Error ? e.message : "Erasure failed."); } finally { setSaving(false); }
  }

  async function handlePurge() {
    if (!canManage) return;
    setSaving(true); setActionError(null); setMessage(null);
    try {
      const res = await api.triggerPurge(activeTenantId, dryRun);
      await refreshLogs(); await refreshRetention();
      setMessage(dryRun ? `Dry run: ${res.purge.records_scanned} scanned, ${res.purge.transcripts_purged} transcripts, ${res.purge.calls_anonymized} calls would be purged.` : `Purge executed: ${res.purge.transcripts_purged} transcripts purged, ${res.purge.calls_anonymized} calls anonymized.`);
    } catch (e) { setActionError(e instanceof Error ? e.message : "Purge failed."); } finally { setSaving(false); }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-16">
      {/* Header */}
      <header className="rounded-2xl border border-white/10 bg-gradient-to-br from-[#0f0f1e]/80 to-[#1a1030]/80 backdrop-blur-xl p-6 shadow-2xl">
        <div className="flex items-start gap-3">
          <div className="rounded-xl border border-[#00ffcc]/25 bg-[#00ffcc]/10 p-2 text-[#00ffcc]"><ShieldCheck size={22} /></div>
          <div>
            <p className="text-xs font-mono text-[#94a3b8]">Privacy & Compliance / {activeTenant.name}</p>
            <h1 className="mt-1 text-2xl font-bold text-white">Privacy & Data Lifecycle</h1>
            <p className="mt-2 max-w-3xl text-sm text-[#94a3b8]">UK GDPR & DPA 2018 compliant data controls — DSAR export, right to erasure, retention lifecycle and audit trail.</p>
            <div className="mt-3 inline-flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-xs font-mono text-emerald-300">🟢 UK GDPR & DPA 2018 Compliant</div>
          </div>
        </div>
      </header>

      {demoMode && <div className="rounded-2xl border border-[#ffe04a]/30 bg-[#ffe04a]/10 p-5 text-sm text-[#fef3c7]">Demo workspace — aggregate preview only. Retention, DSAR and purge require owner role.</div>}
      {!demoMode && !canManage && <div className="rounded-2xl border border-white/10 bg-white/5 p-5 text-sm text-[#a098b0]">Viewer / operator: you can export DSAR bundles, but retention and erasure require owner.</div>}

      {/* Metrics */}
      <section className="grid gap-4 md:grid-cols-3">
        <Metric label="Call records scanned" value={overview?.preview.call_records_scanned} />
        <Metric label="Eligible for transcript purge" value={overview?.preview.transcript_records_eligible_for_review} />
        <Metric label="Purge logs" value={purgeLogs?.logs.length} />
      </section>

      {/* GDPR Data Subject Rights Card */}
      <section className="rounded-2xl border border-white/10 bg-[#141422]/80 backdrop-blur-xl p-6 shadow-xl">
        <div className="flex items-center gap-2"><FileOutput size={18} className="text-[#00ffcc]" /><h2 className="font-bold text-white">GDPR Data Subject Rights</h2></div>
        <p className="mt-1 text-xs text-[#94a3b8]">Lookup by phone or email. Export is owner/operator, erasure is owner-only with confirmation.</p>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Phone or email (e.g. +44 7911 123456)" className="flex-1 rounded-xl border border-white/10 bg-[#181826] px-3 py-2.5 text-sm text-white placeholder:text-[#64748b] focus:border-[#00ffcc] focus:outline-none" />
          <button onClick={() => void handleExport()} disabled={saving || !subject.trim() || !canExport} className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#00ffcc] px-4 py-2.5 text-sm font-bold text-[#061313] disabled:opacity-40"><Download size={16} />Download DSAR Export</button>
          <button onClick={() => setShowEraseModal(true)} disabled={!subject.trim() || !canManage} className="inline-flex items-center justify-center gap-2 rounded-xl border border-red-400/40 px-4 py-2.5 text-sm font-bold text-red-300 hover:bg-red-400/10 disabled:opacity-40"><EyeOff size={16} />Erase Caller Data</button>
        </div>
      </section>

      {/* Retention Settings Card */}
      <section className="rounded-2xl border border-white/10 bg-[#141422]/80 backdrop-blur-xl p-6 shadow-xl">
        <div className="flex items-center gap-2"><Database size={18} className="text-[#00ffcc]" /><h2 className="font-bold text-white">Data Retention & Lifecycle</h2></div>
        <div className="mt-5 grid gap-6 md:grid-cols-2">
          <div>
            <label className="text-xs font-mono uppercase tracking-wider text-[#94a3b8]">Transcript retention (days)</label>
            <div className="mt-2 flex flex-wrap gap-2">
              {TRANSCRIPT_OPTIONS.map((v) => (
                <button key={v} onClick={() => setRetention((c) => ({ ...c, transcript_retention_days: v }))} className={`rounded-full px-3 py-1.5 text-xs font-bold border ${retention.transcript_retention_days === v ? "bg-[#00ffcc] text-[#061313] border-[#00ffcc]" : "border-white/10 text-[#94a3b8] hover:border-[#00ffcc]/40"}`}>{v}d</button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs font-mono uppercase tracking-wider text-[#94a3b8]">Call record retention (days)</label>
            <div className="mt-2 flex flex-wrap gap-2">
              {CALL_OPTIONS.map((v) => (
                <button key={v} onClick={() => setRetention((c) => ({ ...c, call_retention_days: v }))} className={`rounded-full px-3 py-1.5 text-xs font-bold border ${retention.call_retention_days === v ? "bg-[#00ffcc] text-[#061313] border-[#00ffcc]" : "border-white/10 text-[#94a3b8] hover:border-[#00ffcc]/40"}`}>{v}d</button>
              ))}
            </div>
          </div>
        </div>
        <label className="mt-5 flex items-center gap-3 cursor-pointer">
          <input type="checkbox" checked={retention.pii_masking_enabled} onChange={(e) => setRetention((c) => ({ ...c, pii_masking_enabled: e.target.checked }))} className="h-4 w-4 accent-[#00ffcc]" />
          <span className="text-sm text-white">PII masking for Google Sheets / webhook exports</span><span className="text-xs text-[#94a3b8]">(+44 7911 *** 456 / j***e@acme.co.uk)</span>
        </label>
        <div className="mt-3 flex items-center gap-2 text-xs text-[#94a3b8]"><Globe size={14} />Data residency: <span className="rounded bg-white/10 px-2 py-0.5 font-mono text-white">{retention.data_residency_region}</span> (eu-west-2 / London)</div>
        <div className="mt-5 flex flex-wrap gap-3">
          <button onClick={() => void saveRetention()} disabled={saving || !canManage} className="rounded-xl bg-white px-4 py-2.5 text-sm font-bold text-[#0f0f1e] disabled:opacity-40">Save Retention Policy</button>
          <label className="flex items-center gap-2 text-xs text-[#94a3b8]"><input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} />Dry run preview</label>
          <button onClick={() => void handlePurge()} disabled={saving || !canManage} className="inline-flex items-center gap-2 rounded-xl border border-[#00ffcc]/40 px-4 py-2.5 text-sm font-bold text-[#bfffee] hover:bg-[#00ffcc]/10 disabled:opacity-40"><Play size={14} />Run Retention Purge Now</button>
        </div>
        {(message || actionError) && <div className={`mt-4 rounded-xl border px-4 py-3 text-sm ${actionError ? "border-red-400/30 bg-red-400/10 text-red-200" : "border-emerald-400/30 bg-emerald-400/10 text-emerald-200"}`}>{actionError || message}</div>}
      </section>

      {/* Sub-Processor & Data Residency Registry */}
      <section className="rounded-2xl border border-white/10 bg-[#141422]/80 backdrop-blur-xl p-6 shadow-xl">
        <div className="flex items-center gap-2"><Building2 size={18} className="text-[#00ffcc]" /><h2 className="font-bold text-white">Sub-Processor & Data Residency Registry</h2></div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {[
            { name: "AWS", detail: "Connect, Lex, Polly — EU / London (eu-west-2)", icon: Server },
            { name: "Groq", detail: "LLM Inference — Zero Data Retention", icon: Brain },
            { name: "Supabase", detail: "PostgreSQL — London eu-west-2", icon: Database },
            { name: "Google Workspace", detail: "Sheets Mirror — Per-tenant isolated", icon: SheetIcon },
          ].map((p) => (
            <div key={p.name} className="rounded-xl border border-white/5 bg-white/5 p-4 flex gap-3">
              <p.icon size={18} className="text-[#94a3b8] mt-0.5" />
              <div><p className="text-sm font-bold text-white">{p.name}</p><p className="text-xs text-[#94a3b8]">{p.detail}</p></div>
            </div>
          ))}
        </div>
      </section>

      {/* Purge History Audit Log */}
      <section className="rounded-2xl border border-white/10 bg-[#141422]/80 backdrop-blur-xl p-6 shadow-xl">
        <div className="flex items-center gap-2"><History size={18} className="text-[#00ffcc]" /><h2 className="font-bold text-white">Purge History Audit Log</h2></div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="border-b border-white/10 text-[10px] font-mono uppercase tracking-wider text-[#94a3b8]"><tr><th className="pb-2">When</th><th className="pb-2">Type</th><th className="pb-2">Scanned</th><th className="pb-2">Transcripts purged</th><th className="pb-2">Calls anonymized</th><th className="pb-2">Dry run</th><th className="pb-2">Operator</th></tr></thead>
            <tbody>
              {(purgeLogs?.logs ?? []).map((log: any) => (
                <tr key={log.id} className="border-b border-white/5 text-[#cbd5e1]"><td className="py-2 text-xs">{log.created_at ? new Date(log.created_at).toLocaleString() : "—"}</td><td className="py-2"><span className="rounded bg-white/10 px-2 py-0.5 text-xs font-mono">{log.execution_type}</span></td><td className="py-2">{log.records_scanned}</td><td className="py-2">{log.transcripts_purged}</td><td className="py-2">{log.calls_anonymized}</td><td className="py-2">{log.dry_run ? "yes" : "no"}</td><td className="py-2 font-mono text-xs">{log.purged_by_user_id ?? "—"}</td></tr>
              ))}
              {(!purgeLogs?.logs || purgeLogs.logs.length === 0) && <tr><td colSpan={7} className="py-6 text-center text-xs text-[#64748b]">No purge executions yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>

      {/* Legacy redacted review ledger */}
      {canManage && requestLedger && requestLedger.requests.length > 0 && (
        <section className="rounded-2xl border border-white/10 bg-[#141422]/80 p-6">
          <h2 className="font-bold text-white">Redacted Review Ledger</h2>
          <div className="mt-3 overflow-x-auto"><table className="w-full min-w-[600px] text-left text-sm"><thead className="border-b border-white/10 text-[10px] font-mono uppercase tracking-wider text-[#94a3b8]"><tr><th className="pb-2">Request</th><th className="pb-2">Type</th><th className="pb-2">Status</th><th className="pb-2">Created</th></tr></thead><tbody>{requestLedger.requests.map((r: any) => <tr key={r.id} className="border-b border-white/5 text-[#cbd5e1]"><td className="py-2 font-mono text-xs">{r.id}</td><td className="py-2">{r.request_type}</td><td className="py-2"><span className="rounded bg-[#00ffcc]/10 px-2 py-0.5 text-xs font-mono text-[#00ffcc]">{r.status}</span></td><td className="py-2 text-xs">{r.created_at ? new Date(r.created_at).toLocaleString() : "—"}</td></tr>)}</tbody></table></div>
        </section>
      )}

      {showEraseModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-[#1a1a2e] p-6 shadow-2xl">
            <h3 className="font-bold text-white">Confirm Erasure</h3>
            <p className="mt-2 text-sm text-[#94a3b8]">This will anonymize PII for <span className="font-mono text-white">{subject}</span> across calls, communications and supplier contacts. Financial order refs are preserved. Type <span className="font-mono text-red-300">DELETE DATA</span> to confirm.</p>
            <input value={confirmText} onChange={(e) => setConfirmText(e.target.value)} placeholder="DELETE DATA" className="mt-4 w-full rounded-xl border border-white/10 bg-[#0f0f1e] px-3 py-2.5 text-sm text-white placeholder:text-[#64748b] focus:border-red-400/50 focus:outline-none" />
            <div className="mt-5 flex justify-end gap-2"><button onClick={() => { setShowEraseModal(false); setConfirmText(""); }} className="rounded-xl border border-white/10 px-4 py-2 text-sm text-[#94a3b8]">Cancel</button><button onClick={() => void handleErase()} disabled={confirmText !== "DELETE DATA" || saving} className="rounded-xl bg-red-600 px-4 py-2 text-sm font-bold text-white disabled:opacity-40">Erase Data</button></div>
          </div>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value?: number }) { return <div className="rounded-2xl border border-white/10 bg-[#141422]/60 backdrop-blur p-5"><p className="text-xs uppercase tracking-wider text-[#94a3b8]">{label}</p><p className="mt-2 text-2xl font-bold text-white">{value ?? "—"}</p></div>; }
function SheetIcon(props: any) { return <FileOutput {...props} />; }
