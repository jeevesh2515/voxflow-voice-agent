"use client";

import { useState } from "react";
import useSWR from "swr";
import { ShieldCheck, UserMinus, UserPlus, UsersRound } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useTenant } from "@/lib/tenant-context";
import type { TenantRole } from "@/lib/types";

const INVITABLE_ROLES: TenantRole[] = ["operator", "viewer"];

function titleCase(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

export default function WorkspaceAccessPage() {
  const { user } = useAuth();
  const { activeTenant, activeTenantId, demoMode } = useTenant();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<TenantRole>("viewer");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const { data, error, isLoading, mutate } = useSWR(
    activeTenantId ? ["tenant-members", activeTenantId] : null,
    () => api.tenantMembers(activeTenantId),
    { revalidateOnFocus: true },
  );

  const canManage = !demoMode && activeTenant.role === "owner";
  const canView = !demoMode && (activeTenant.role === "owner" || activeTenant.role === "operator");

  async function inviteMember(event: React.FormEvent) {
    event.preventDefault();
    if (!canManage || !email.trim()) return;
    setSubmitting(true);
    setActionError(null);
    setMessage(null);
    try {
      const result = await api.inviteTenantMember(activeTenantId, { email: email.trim(), role });
      setEmail("");
      setMessage(`Invitation recorded for manual delivery. The recipient must sign in and accept access before becoming active.`);
      await mutate();
      if (!result.created) setMessage("The pending membership was refreshed. Manual invitation delivery is still required.");
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Unable to record the membership invitation.");
    } finally {
      setSubmitting(false);
    }
  }

  async function revokeMember(userId: string) {
    if (!canManage) return;
    setActionError(null);
    setMessage(null);
    try {
      await api.revokeTenantMember(activeTenantId, userId);
      setMessage("Member access was revoked. The membership ledger remains available for audit.");
      await mutate();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Unable to revoke the membership.");
    }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 pb-16">
      <header className="rounded-2xl border border-[#28283c] bg-[#141422] p-6">
        <div className="flex items-start gap-3">
          <div className="rounded-xl border border-[#00ffcc]/25 bg-[#00ffcc]/10 p-2 text-[#00ffcc]"><ShieldCheck size={20} /></div>
          <div>
            <p className="text-xs font-mono text-[#94a3b8]">Workspace access / {activeTenant.name}</p>
            <h1 className="mt-1 text-2xl font-bold text-white">Tenant Memberships</h1>
            <p className="mt-2 max-w-2xl text-sm text-[#94a3b8]">Access is determined by an application-owned membership ledger, not by a browser workspace selector or editable account metadata.</p>
          </div>
        </div>
      </header>

      {demoMode ? (
        <div className="rounded-2xl border border-[#ffe04a]/30 bg-[#ffe04a]/10 p-5 text-sm text-[#fef3c7]">The demonstration workspace is strictly read-only. It cannot display real membership records, create invitations, revoke access, configure providers, or activate operations.</div>
      ) : !canView ? (
        <div className="rounded-2xl border border-[#ff2d78]/30 bg-[#ff2d78]/10 p-5 text-sm text-[#fecdd3]">Your current role does not permit membership visibility. Ask a workspace owner to review access.</div>
      ) : (
        <>
          {canManage && (
            <section className="rounded-2xl border border-[#28283c] bg-[#141422] p-6">
              <div className="flex items-center gap-2"><UserPlus size={18} className="text-[#00ffcc]" /><h2 className="font-headline text-base font-bold text-white">Record a Membership Invitation</h2></div>
              <p className="mt-2 text-xs text-[#94a3b8]">VoxFlow records a pending invitation without sending an email. Deliver access through your approved design-partner process; the signed-in recipient must accept it.</p>
              <form onSubmit={inviteMember} className="mt-5 grid gap-3 sm:grid-cols-[1fr_150px_auto]">
                <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required placeholder="teammate@company.com" className="rounded-xl border border-[#302840]/60 bg-[#181826] px-3 py-2.5 text-sm text-white placeholder:text-[#64748b] focus:border-[#00ffcc] focus:outline-none" />
                <select value={role} onChange={(event) => setRole(event.target.value as TenantRole)} className="rounded-xl border border-[#302840]/60 bg-[#181826] px-3 py-2.5 text-sm text-white focus:border-[#00ffcc] focus:outline-none">
                  {INVITABLE_ROLES.map((option) => <option key={option} value={option}>{titleCase(option)}</option>)}
                </select>
                <button type="submit" disabled={submitting} className="rounded-xl bg-[#00ffcc] px-4 py-2.5 text-sm font-bold text-[#061313] transition-opacity hover:opacity-90 disabled:opacity-50">{submitting ? "Recording…" : "Record Invitation"}</button>
              </form>
            </section>
          )}

          {(actionError || message) && <div className={`rounded-xl border px-4 py-3 text-sm ${actionError ? "border-[#ff2d78]/40 bg-[#ff2d78]/10 text-[#fecdd3]" : "border-[#00ffcc]/30 bg-[#00ffcc]/10 text-[#bfffee]"}`}>{actionError || message}</div>}

          <section className="rounded-2xl border border-[#28283c] bg-[#141422] p-6">
            <div className="flex items-center gap-2"><UsersRound size={18} className="text-[#00ffcc]" /><h2 className="font-headline text-base font-bold text-white">Membership Ledger</h2></div>
            <p className="mt-2 text-xs text-[#94a3b8]">Raw invitee email addresses are not displayed. Revocation keeps an auditable lifecycle record and protects the final active owner.</p>
            {error ? <p className="mt-5 text-sm text-[#fecdd3]">Memberships could not be loaded.</p> : isLoading ? <p className="mt-5 text-sm text-[#94a3b8]">Loading server-authorized memberships…</p> : (
              <div className="mt-5 overflow-x-auto"><table className="w-full min-w-[620px] text-left text-sm"><thead className="border-b border-[#2c2c40] text-[10px] font-mono uppercase tracking-wider text-[#94a3b8]"><tr><th className="pb-3 pr-4">Member ID</th><th className="pb-3 pr-4">Role</th><th className="pb-3 pr-4">Status</th><th className="pb-3 pr-4">Activated</th><th className="pb-3 text-right">Action</th></tr></thead><tbody>{data?.members.map((member) => <tr key={member.id} className="border-b border-[#242436] text-[#cbd5e1]"><td className="py-3 pr-4 font-mono text-xs">{member.user_id || "Pending acceptance"}</td><td className="py-3 pr-4">{titleCase(member.role)}</td><td className="py-3 pr-4"><span className={`rounded-md px-2 py-1 text-[11px] font-mono ${member.status === "active" ? "bg-[#00ffcc]/10 text-[#00ffcc]" : member.status === "revoked" ? "bg-[#ff2d78]/10 text-[#ff9bbd]" : "bg-[#ffe04a]/10 text-[#ffe04a]"}`}>{member.status.toUpperCase()}</span></td><td className="py-3 pr-4 text-xs text-[#94a3b8]">{member.activated_at ? new Date(member.activated_at).toLocaleString() : "—"}</td><td className="py-3 text-right">{canManage && member.status === "active" && member.user_id && member.user_id !== user?.id ? <button type="button" onClick={() => void revokeMember(member.user_id!)} className="inline-flex items-center gap-1 rounded-lg border border-[#ff2d78]/35 px-2.5 py-1.5 text-xs font-semibold text-[#ff9bbd] hover:bg-[#ff2d78]/10"><UserMinus size={13} />Revoke</button> : <span className="text-xs text-[#64748b]">—</span>}</td></tr>)}</tbody></table></div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
