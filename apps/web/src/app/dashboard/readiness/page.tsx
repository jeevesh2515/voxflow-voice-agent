"use client";

import useSWR from "swr";
import { ClipboardCheck, Lock, ShieldCheck, TriangleAlert } from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";

export default function ReadinessPage() {
  const { activeTenant, activeTenantId } = useTenant();
  const { data, error, isLoading } = useSWR(
    activeTenantId ? ["design-partner-readiness", activeTenantId] : null,
    () => api.designPartnerReadiness(activeTenantId),
  );

  return (
    <div className="mx-auto max-w-6xl space-y-6 pb-16">
      <header className="rounded-2xl border border-[#28283c] bg-[#141422] p-6"><div className="flex items-start gap-3"><div className="rounded-xl border border-[#00ffcc]/25 bg-[#00ffcc]/10 p-2 text-[#00ffcc]"><ClipboardCheck size={20} /></div><div><p className="text-xs font-mono text-[#94a3b8]">Design-partner readiness / {activeTenant.name}</p><h1 className="mt-1 text-2xl font-bold text-white">Controlled Pilot Gates</h1><p className="mt-2 max-w-3xl text-sm text-[#94a3b8]">This scorecard reports evidence and blockers only. It cannot approve a pilot, create a cohort, enable a provider, register callbacks, start workers, or place an outbound call.</p></div></div></header>
      {error ? <Notice tone="error" text="Readiness evidence could not be loaded." /> : isLoading ? <Notice tone="neutral" text="Loading non-executable readiness evidence…" /> : data ? <>
        <section className="grid gap-4 md:grid-cols-4"><Metric label="Overall status" value={data.status.replace(/_/g, " ")} /><Metric label="Active owners" value={String(data.summary.active_owner_count)} /><Metric label="Reliability" value={data.summary.reliability_status} /><Metric label="Provider activity" value={data.summary.provider_activity_enabled ? "enabled" : "disabled"} /></section>
        <section className="rounded-2xl border border-[#28283c] bg-[#141422] p-6"><div className="flex items-center gap-2"><ShieldCheck size={18} className="text-[#00ffcc]" /><h2 className="font-headline text-base font-bold text-white">Software Safety Posture</h2></div><div className="mt-4 grid gap-3 sm:grid-cols-3"><Status label="Campaign worker" value={data.summary.campaign_worker_enabled ? "enabled" : "disabled"} safe={!data.summary.campaign_worker_enabled} /><Status label="Side-effect worker" value={data.summary.side_effect_worker_enabled ? "enabled" : "disabled"} safe={!data.summary.side_effect_worker_enabled} /><Status label="Automatic activation" value={data.automatic_activation ? "enabled" : "disabled"} safe={!data.automatic_activation} /></div></section>
        <section className="rounded-2xl border border-[#28283c] bg-[#141422] p-6"><div className="flex items-center gap-2"><Lock size={18} className="text-[#ffe04a]" /><h2 className="font-headline text-base font-bold text-white">Readiness Gate Ledger</h2></div><p className="mt-2 text-xs text-[#94a3b8]">Blocked human and paid-provider gates are deliberately not controllable from this dashboard.</p><div className="mt-5 space-y-3">{data.gates.map((gate) => <div key={gate.code} className="rounded-xl border border-[#302840]/60 bg-[#181826] p-4"><div className="flex flex-wrap items-center gap-2"><span className={`rounded-md px-2 py-1 text-[10px] font-mono uppercase ${gate.status === "ready" ? "bg-[#00ffcc]/10 text-[#00ffcc]" : gate.status === "attention" ? "bg-[#ffe04a]/10 text-[#ffe04a]" : "bg-[#ff2d78]/10 text-[#ff9bbd]"}`}>{gate.status}</span><span className="text-sm font-semibold text-white">{gate.code.replace(/_/g, " ")}</span><span className="text-[10px] font-mono uppercase text-[#64748b]">{gate.category.replace(/_/g, " ")}</span></div><p className="mt-2 text-sm text-[#a098b0]">{gate.detail}</p><p className="mt-2 text-xs text-[#64748b]">Owner: {gate.owner}</p></div>)}</div></section>
        <Notice tone="warning" text={data.next_step} />
      </> : null}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) { return <div className="rounded-2xl border border-[#28283c] bg-[#141422] p-5"><p className="text-[10px] font-mono uppercase tracking-wider text-[#94a3b8]">{label}</p><p className="mt-2 text-lg font-bold capitalize text-white">{value}</p></div>; }
function Status({ label, value, safe }: { label: string; value: string; safe: boolean }) { return <div className="rounded-xl border border-[#302840]/60 bg-[#181826] p-4"><p className="text-[10px] uppercase tracking-wider text-[#94a3b8]">{label}</p><p className={`mt-1 font-mono text-sm ${safe ? "text-[#00ffcc]" : "text-[#ff9bbd]"}`}>{value}</p></div>; }
function Notice({ tone, text }: { tone: "error" | "neutral" | "warning"; text: string }) { const styles = { error: "border-[#ff2d78]/30 bg-[#ff2d78]/10 text-[#fecdd3]", neutral: "border-[#28283c] bg-[#141422] text-[#a098b0]", warning: "border-[#ffe04a]/30 bg-[#ffe04a]/10 text-[#fef3c7]" }; return <div className={`rounded-xl border px-4 py-3 text-sm ${styles[tone]}`}><span className="inline-flex items-center gap-2">{tone === "warning" && <TriangleAlert size={16} />}{text}</span></div>; }
