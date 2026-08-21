"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";
import { FileLock2, FileOutput, RotateCcw, ShieldCheck, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";
import type { PrivacyRequestType } from "@/lib/types";

export default function PrivacyControlsPage() {
  const { activeTenant, activeTenantId, demoMode } = useTenant();
  const [retention, setRetention] = useState({ call_transcript_retention_days: 30, communication_retention_days: 30, recording_retention_days: 0 });
  const [subjectReference, setSubjectReference] = useState("");
  const [requestType, setRequestType] = useState<Extract<PrivacyRequestType, "access_export" | "deletion">>("access_export");
  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const { data: overview, mutate: refreshOverview } = useSWR(
    activeTenantId ? ["privacy-overview", activeTenantId] : null,
    () => api.privacyOverview(activeTenantId),
  );
  const { data: resetPreview } = useSWR(
    activeTenantId ? ["privacy-reset-preview", activeTenantId] : null,
    () => api.demoResetPreview(activeTenantId),
  );
  const canManage = !demoMode && activeTenant.role === "owner";
  const { data: requestLedger, mutate: refreshRequests } = useSWR(
    canManage && activeTenantId ? ["privacy-requests", activeTenantId] : null,
    () => api.privacyRequests(activeTenantId),
  );

  useEffect(() => {
    if (overview?.policy) {
      setRetention({
        call_transcript_retention_days: overview.policy.call_transcript_retention_days,
        communication_retention_days: overview.policy.communication_retention_days,
        recording_retention_days: overview.policy.recording_retention_days,
      });
    }
  }, [overview?.policy]);

  async function updatePolicy(event: React.FormEvent) {
    event.preventDefault();
    if (!canManage) return;
    setSaving(true); setActionError(null); setMessage(null);
    try {
      await api.updatePrivacyPolicy(activeTenantId, retention);
      await refreshOverview();
      setMessage("Retention policy saved. No purge, worker, provider, recording retrieval, or export was triggered.");
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Unable to save the retention policy.");
    } finally { setSaving(false); }
  }

  async function createRequest(event: React.FormEvent) {
    event.preventDefault();
    if (!canManage || !subjectReference.trim()) return;
    setSaving(true); setActionError(null); setMessage(null);
    try {
      await api.createPrivacyRequest(activeTenantId, { request_type: requestType, subject_reference: subjectReference.trim() });
      setSubjectReference("");
      await refreshRequests();
      setMessage("A redacted request was recorded for human verification. No export or deletion was performed.");
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Unable to record the privacy request.");
    } finally { setSaving(false); }
  }

  async function requestDemoReset() {
    if (!canManage) return;
    setSaving(true); setActionError(null); setMessage(null);
    try {
      await api.createDemoResetRequest(activeTenantId);
      await refreshRequests();
      setMessage("A blocked demo-reset request was recorded. No data was reset or deleted.");
    } catch (error) {
      setActionError(error instanceof Error ? error.message : "Unable to record the demo-reset request.");
    } finally { setSaving(false); }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-16">
      <header className="rounded-2xl border border-[#28283c] bg-[#141422] p-6">
        <div className="flex items-start gap-3"><div className="rounded-xl border border-[#00ffcc]/25 bg-[#00ffcc]/10 p-2 text-[#00ffcc]"><ShieldCheck size={20} /></div><div><p className="text-xs font-mono text-[#94a3b8]">Privacy controls / {activeTenant.name}</p><h1 className="mt-1 text-2xl font-bold text-white">Retention and Data-Subject Requests</h1><p className="mt-2 max-w-3xl text-sm text-[#94a3b8]">This workspace exposes aggregate evidence and a redacted review ledger only. Actual data export, deletion, recording access, and demonstration reset are intentionally not automated.</p></div></div>
      </header>

      {demoMode && <div className="rounded-2xl border border-[#ffe04a]/30 bg-[#ffe04a]/10 p-5 text-sm text-[#fef3c7]">The demonstration workspace can display only aggregate privacy preview evidence. It cannot view a request ledger, set retention, request deletion, export data, or reset records.</div>}
      {!demoMode && !canManage && <div className="rounded-2xl border border-[#28283c] bg-[#141422] p-5 text-sm text-[#a098b0]">Your current role can view aggregate retention evidence only. A tenant owner must record privacy requests or update retention settings.</div>}

      <section className="grid gap-4 md:grid-cols-3">
        <Metric label="Call records scanned" value={overview?.preview.call_records_scanned} />
        <Metric label="Transcript records eligible for review" value={overview?.preview.transcript_records_eligible_for_review} />
        <Metric label="Communication records eligible for review" value={overview?.preview.communication_records_eligible_for_review} />
      </section>

      <section className="rounded-2xl border border-[#28283c] bg-[#141422] p-6">
        <div className="flex items-center gap-2"><FileLock2 size={18} className="text-[#00ffcc]" /><h2 className="font-headline text-base font-bold text-white">Retention Preview</h2></div>
        <p className="mt-2 text-xs text-[#94a3b8]">The displayed counts are aggregate-only. The preview cannot enqueue a purge or access a provider recording.</p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm"><Status label="Mode" value={overview?.execution.mode || "loading"} /><Status label="Purge job" value={overview?.execution.purge_job_enqueued ? "queued" : "not queued"} /><Status label="Provider access" value={overview?.execution.provider_accessed ? "used" : "not used"} /><Status label="Raw record export" value={overview?.execution.raw_record_exported ? "performed" : "not performed"} /></div>
      </section>

      {canManage && <section className="grid gap-6 lg:grid-cols-2">
        <form onSubmit={updatePolicy} className="rounded-2xl border border-[#28283c] bg-[#141422] p-6"><h2 className="font-headline text-base font-bold text-white">Retention Policy</h2><p className="mt-2 text-xs text-[#94a3b8]">Saving policy controls creates no destructive action. All values are days.</p><div className="mt-5 grid gap-3"><NumberInput label="Call transcript retention" value={retention.call_transcript_retention_days} onChange={(value) => setRetention((current) => ({ ...current, call_transcript_retention_days: value }))} /><NumberInput label="Communication retention" value={retention.communication_retention_days} onChange={(value) => setRetention((current) => ({ ...current, communication_retention_days: value }))} /><NumberInput label="Recording retention" value={retention.recording_retention_days} onChange={(value) => setRetention((current) => ({ ...current, recording_retention_days: value }))} /></div><button disabled={saving} className="mt-5 rounded-xl bg-[#00ffcc] px-4 py-2.5 text-sm font-bold text-[#061313] disabled:opacity-50">Save Policy</button></form>
        <form onSubmit={createRequest} className="rounded-2xl border border-[#28283c] bg-[#141422] p-6"><div className="flex items-center gap-2"><FileOutput size={18} className="text-[#00ffcc]" /><h2 className="font-headline text-base font-bold text-white">Record Data-Subject Request</h2></div><p className="mt-2 text-xs text-[#94a3b8]">The subject reference is hashed by the server and is never shown in the request ledger. A separate authorized human process is required for every actual action.</p><div className="mt-5 space-y-3"><select value={requestType} onChange={(event) => setRequestType(event.target.value as Extract<PrivacyRequestType, "access_export" | "deletion">)} className="w-full rounded-xl border border-[#302840]/60 bg-[#181826] px-3 py-2.5 text-sm text-white"><option value="access_export">Access / export request</option><option value="deletion">Deletion request</option></select><input value={subjectReference} onChange={(event) => setSubjectReference(event.target.value)} required placeholder="Subject reference (hashed; not retained here)" className="w-full rounded-xl border border-[#302840]/60 bg-[#181826] px-3 py-2.5 text-sm text-white placeholder:text-[#64748b] focus:border-[#00ffcc] focus:outline-none" /></div><button disabled={saving} className="mt-5 inline-flex items-center gap-2 rounded-xl border border-[#00ffcc]/40 px-4 py-2.5 text-sm font-bold text-[#bfffee] hover:bg-[#00ffcc]/10 disabled:opacity-50"><Trash2 size={15} />Record for Human Review</button></form>
      </section>}

      {canManage && activeTenantId === "varun" && <section className="rounded-2xl border border-[#ffe04a]/30 bg-[#ffe04a]/5 p-6"><div className="flex items-center gap-2"><RotateCcw size={18} className="text-[#ffe04a]" /><h2 className="font-headline text-base font-bold text-white">Sanitized Demo Reset</h2></div><p className="mt-2 text-xs text-[#94a3b8]">This control can only record a blocked request. It cannot reset a demo, delete data, contact a provider, or start any worker.</p><div className="mt-4 grid gap-2 text-xs">{resetPreview?.gates.map((gate) => <div key={gate.code} className="rounded-lg border border-[#302840]/60 bg-[#181826] p-3 text-[#a098b0]"><strong className={gate.met ? "text-[#00ffcc]" : "text-[#ffe04a]"}>{gate.met ? "Met" : "Blocked"}</strong> · {gate.detail}</div>)}</div><button onClick={() => void requestDemoReset()} disabled={saving} className="mt-5 rounded-xl border border-[#ffe04a]/40 px-4 py-2.5 text-sm font-bold text-[#fef3c7] hover:bg-[#ffe04a]/10 disabled:opacity-50">Record Blocked Reset Request</button></section>}

      {(message || actionError) && <div className={`rounded-xl border px-4 py-3 text-sm ${actionError ? "border-[#ff2d78]/40 bg-[#ff2d78]/10 text-[#fecdd3]" : "border-[#00ffcc]/30 bg-[#00ffcc]/10 text-[#bfffee]"}`}>{actionError || message}</div>}

      {canManage && <section className="rounded-2xl border border-[#28283c] bg-[#141422] p-6"><h2 className="font-headline text-base font-bold text-white">Redacted Review Ledger</h2><p className="mt-2 text-xs text-[#94a3b8]">Identifiers and request state are available for audit; raw subject references and hash values are intentionally not shown.</p><div className="mt-5 overflow-x-auto"><table className="w-full min-w-[700px] text-left text-sm"><thead className="border-b border-[#2c2c40] text-[10px] font-mono uppercase tracking-wider text-[#94a3b8]"><tr><th className="pb-3 pr-4">Request</th><th className="pb-3 pr-4">Type</th><th className="pb-3 pr-4">Status</th><th className="pb-3 pr-4">Created</th><th className="pb-3">Review note</th></tr></thead><tbody>{requestLedger?.requests.map((request) => <tr key={request.id} className="border-b border-[#242436] text-[#cbd5e1]"><td className="py-3 pr-4 font-mono text-xs">{request.id}</td><td className="py-3 pr-4">{request.request_type.replace(/_/g, " ")}</td><td className="py-3 pr-4"><span className="rounded-md bg-[#00ffcc]/10 px-2 py-1 text-[11px] font-mono text-[#00ffcc]">{request.status.replace(/_/g, " ")}</span></td><td className="py-3 pr-4 text-xs text-[#94a3b8]">{request.created_at ? new Date(request.created_at).toLocaleString() : "—"}</td><td className="py-3 text-xs text-[#94a3b0]">{request.review_note || "—"}</td></tr>)}</tbody></table></div></section>}
    </div>
  );
}

function Metric({ label, value }: { label: string; value?: number }) { return <div className="rounded-2xl border border-[#28283c] bg-[#141422] p-5"><p className="text-xs uppercase tracking-wider text-[#94a3b8]">{label}</p><p className="mt-2 text-2xl font-bold text-white">{value ?? "—"}</p></div>; }
function Status({ label, value }: { label: string; value: string }) { return <div className="rounded-xl border border-[#302840]/60 bg-[#181826] p-3"><p className="text-[10px] uppercase tracking-wider text-[#94a3b8]">{label}</p><p className="mt-1 font-mono text-xs text-[#bfffee]">{value}</p></div>; }
function NumberInput({ label, value, onChange }: { label: string; value: number; onChange: (value: number) => void }) { return <label className="grid gap-1.5 text-xs text-[#a098b0]"><span>{label}</span><input type="number" min="0" max="3650" value={value} onChange={(event) => onChange(Number(event.target.value))} className="rounded-xl border border-[#302840]/60 bg-[#181826] px-3 py-2.5 text-sm text-white focus:border-[#00ffcc] focus:outline-none" /></label>; }
