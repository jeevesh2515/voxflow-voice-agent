"use client";

import { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Crown,
  Eye,
  Headphones,
  Lock,
  Plus,
  RefreshCw,
  Shield,
  Trash2,
  UserCheck,
  UserPlus,
  Users,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";
import { TenantMembership, TenantRole } from "@/lib/types";

function roleColor(role: TenantRole): { bg: string; text: string; border: string; icon: typeof Crown } {
  switch (role) {
    case "owner":
      return { bg: "bg-[#ff2d78]/10", text: "text-[#ff2d78]", border: "border-[#ff2d78]/30", icon: Crown };
    case "operator":
      return { bg: "bg-[#a855f7]/10", text: "text-[#c084fc]", border: "border-[#a855f7]/30", icon: Headphones };
    case "viewer":
    default:
      return { bg: "bg-[#00ffcc]/10", text: "text-[#00ffcc]", border: "border-[#00ffcc]/30", icon: Eye };
  }
}

function statusBadge(status: string): { bg: string; text: string; label: string } {
  switch (status) {
    case "active":
      return { bg: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30", text: "text-emerald-400", label: "Active" };
    case "invited":
      return { bg: "bg-amber-500/10 text-amber-400 border-amber-500/30", text: "text-amber-400", label: "Invited" };
    case "revoked":
    default:
      return { bg: "bg-slate-500/10 text-slate-400 border-slate-500/30", text: "text-slate-400", label: "Revoked" };
  }
}

export default function TeamMembersSettings() {
  const { activeTenant, demoMode } = useTenant();
  const [members, setMembers] = useState<TenantMembership[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Invite modal state
  const [isInviteOpen, setIsInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<TenantRole>("operator");
  const [inviteUserId, setInviteUserId] = useState("");
  const [inviting, setInviting] = useState(false);

  // Role edit / revoke state
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [confirmRevokeMember, setConfirmRevokeMember] = useState<TenantMembership | null>(null);
  const [showMatrix, setShowMatrix] = useState(false);

  const isOwner = activeTenant.role === "owner" && !demoMode;

  const fetchMembers = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.tenantMembers(activeTenant.id);
      setMembers(res.members || []);
    } catch (err: any) {
      setError(err?.message || "Failed to load workspace members");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTenant?.id) {
      fetchMembers();
    }
  }, [activeTenant?.id]);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;

    try {
      setInviting(true);
      setError(null);
      setSuccess(null);
      await api.inviteTenantMember(activeTenant.id, {
        email: inviteEmail.trim(),
        role: inviteRole,
        user_id: inviteUserId.trim() || undefined,
      });
      setSuccess(`Invitation created for ${inviteEmail.trim()} as ${inviteRole.toUpperCase()}`);
      setIsInviteOpen(false);
      setInviteEmail("");
      setInviteUserId("");
      setInviteRole("operator");
      await fetchMembers();
    } catch (err: any) {
      setError(err?.message || "Failed to create invitation");
    } finally {
      setInviting(false);
    }
  };

  const handleRoleChange = async (userId: string, newRole: TenantRole) => {
    try {
      setActionLoading(userId);
      setError(null);
      setSuccess(null);
      await api.updateTenantMemberRole(activeTenant.id, userId, newRole);
      setSuccess(`Member role updated to ${newRole.toUpperCase()}`);
      await fetchMembers();
    } catch (err: any) {
      setError(err?.message || "Failed to update member role");
    } finally {
      setActionLoading(null);
    }
  };

  const handleRevoke = async (member: TenantMembership) => {
    if (!member.user_id) return;
    try {
      setActionLoading(member.user_id);
      setError(null);
      setSuccess(null);
      await api.revokeTenantMember(activeTenant.id, member.user_id);
      setSuccess(`Revoked access for member ${member.user_id}`);
      setConfirmRevokeMember(null);
      await fetchMembers();
    } catch (err: any) {
      setError(err?.message || "Failed to revoke member");
    } finally {
      setActionLoading(null);
    }
  };

  return (
    <section className="overflow-hidden rounded-2xl border border-[#28283c] bg-[#141422]">
      {/* Header */}
      <div className="flex flex-col gap-4 border-b border-[#28283c] bg-[#0f0f1a] p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
        <div className="flex items-center gap-3">
          <div className="rounded-xl border border-[#a855f7]/25 bg-[#a855f7]/10 p-2.5 text-[#c084fc]">
            <Users size={20} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-white">Team Members & Access Control</h2>
              <span className="rounded-md border border-[#a855f7]/30 bg-[#a855f7]/10 px-2 py-0.5 text-[10px] font-mono text-[#c084fc]">
                Day 50 · RBAC Hardened
              </span>
            </div>
            <p className="mt-0.5 text-xs text-[#94a3b8]">
              Manage workspace access roles (Owner, Operator, Viewer) with server-enforced tenant isolation.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setShowMatrix(!showMatrix)}
            className="flex items-center gap-1.5 rounded-lg border border-[#302840] bg-[#1e1e30] px-3 py-2 text-xs font-medium text-[#94a3b8] transition hover:border-[#ff2d78]/30 hover:text-white"
          >
            <Shield size={14} className="text-[#00ffcc]" />
            Permissions Matrix
            {showMatrix ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>

          <button
            type="button"
            onClick={fetchMembers}
            disabled={loading}
            title="Refresh members"
            className="rounded-lg border border-[#302840] bg-[#1e1e30] p-2 text-[#94a3b8] transition hover:text-white disabled:opacity-50"
          >
            <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          </button>

          {isOwner && (
            <button
              type="button"
              onClick={() => setIsInviteOpen(true)}
              className="flex items-center gap-1.5 rounded-lg border border-[#ff2d78]/40 bg-[#ff2d78] px-3.5 py-2 text-xs font-bold text-white shadow-lg shadow-[#ff2d78]/20 transition hover:bg-[#ff2d78]/90"
            >
              <UserPlus size={14} />
              Invite Member
            </button>
          )}
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="mx-5 mt-5 flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3.5 text-xs text-rose-300 sm:mx-6">
          <AlertCircle size={16} className="shrink-0 text-rose-400" />
          <span>{error}</span>
          <button type="button" onClick={() => setError(null)} className="ml-auto text-rose-400 hover:text-white">
            <X size={14} />
          </button>
        </div>
      )}

      {success && (
        <div className="mx-5 mt-5 flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3.5 text-xs text-emerald-300 sm:mx-6">
          <CheckCircle2 size={16} className="shrink-0 text-emerald-400" />
          <span>{success}</span>
          <button type="button" onClick={() => setSuccess(null)} className="ml-auto text-emerald-400 hover:text-white">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Permissions Matrix Accordion */}
      {showMatrix && (
        <div className="border-b border-[#28283c] bg-[#0c0c16] p-5 sm:p-6">
          <h3 className="text-xs font-bold uppercase tracking-wider text-[#94a3b8]">Role Permissions Matrix (Release Gate #3)</h3>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-[#ff2d78]/25 bg-[#ff2d78]/5 p-4">
              <div className="flex items-center gap-2 text-[#ff2d78]">
                <Crown size={16} />
                <h4 className="text-sm font-bold">Owner</h4>
              </div>
              <p className="mt-1 text-[11px] text-[#94a3b8]">Full administrative authority</p>
              <ul className="mt-2.5 space-y-1 text-[11px] text-[#cbd5e1]">
                <li className="flex items-center gap-1.5"><CheckCircle2 size={12} className="text-emerald-400" /> Billing & Plan Controls</li>
                <li className="flex items-center gap-1.5"><CheckCircle2 size={12} className="text-emerald-400" /> Agent Persona & Prompts</li>
                <li className="flex items-center gap-1.5"><CheckCircle2 size={12} className="text-emerald-400" /> Exact DID Phone Routing</li>
                <li className="flex items-center gap-1.5"><CheckCircle2 size={12} className="text-emerald-400" /> Caller Verification PINs</li>
                <li className="flex items-center gap-1.5"><CheckCircle2 size={12} className="text-emerald-400" /> Team Invitations & RBAC</li>
                <li className="flex items-center gap-1.5"><CheckCircle2 size={12} className="text-emerald-400" /> Full Data CRUD & Ingestion</li>
              </ul>
            </div>

            <div className="rounded-xl border border-[#a855f7]/25 bg-[#a855f7]/5 p-4">
              <div className="flex items-center gap-2 text-[#c084fc]">
                <Headphones size={16} />
                <h4 className="text-sm font-bold">Operator (Staff)</h4>
              </div>
              <p className="mt-1 text-[11px] text-[#94a3b8]">Day-to-day operations & escalations</p>
              <ul className="mt-2.5 space-y-1 text-[11px] text-[#cbd5e1]">
                <li className="flex items-center gap-1.5"><CheckCircle2 size={12} className="text-emerald-400" /> Orders & Stock Management</li>
                <li className="flex items-center gap-1.5"><CheckCircle2 size={12} className="text-emerald-400" /> Supplier & Shipments CRUD</li>
                <li className="flex items-center gap-1.5"><CheckCircle2 size={12} className="text-emerald-400" /> Claim & Resolve Escalations</li>
                <li className="flex items-center gap-1.5"><CheckCircle2 size={12} className="text-emerald-400" /> CSV Ingestion (without PINs)</li>
                <li className="flex items-center gap-1.5"><Lock size={12} className="text-rose-400" /> Cannot change settings/DIDs</li>
                <li className="flex items-center gap-1.5"><Lock size={12} className="text-rose-400" /> Cannot manage team members</li>
              </ul>
            </div>

            <div className="rounded-xl border border-[#00ffcc]/25 bg-[#00ffcc]/5 p-4">
              <div className="flex items-center gap-2 text-[#00ffcc]">
                <Eye size={16} />
                <h4 className="text-sm font-bold">Viewer</h4>
              </div>
              <p className="mt-1 text-[11px] text-[#94a3b8]">Read-only audits & observability</p>
              <ul className="mt-2.5 space-y-1 text-[11px] text-[#cbd5e1]">
                <li className="flex items-center gap-1.5"><CheckCircle2 size={12} className="text-emerald-400" /> View Orders, Stock & Suppliers</li>
                <li className="flex items-center gap-1.5"><CheckCircle2 size={12} className="text-emerald-400" /> View Call History & Transcripts</li>
                <li className="flex items-center gap-1.5"><CheckCircle2 size={12} className="text-emerald-400" /> View Analytics & Health KPIs</li>
                <li className="flex items-center gap-1.5"><CheckCircle2 size={12} className="text-emerald-400" /> View Escalation Queue</li>
                <li className="flex items-center gap-1.5"><Lock size={12} className="text-rose-400" /> Read-only (All writes blocked)</li>
                <li className="flex items-center gap-1.5"><Lock size={12} className="text-rose-400" /> Zero administrative access</li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Members Table */}
      <div className="p-5 sm:p-6">
        {loading ? (
          <div className="flex items-center justify-center py-10 text-xs text-[#94a3b8]">
            <RefreshCw size={18} className="mr-2 animate-spin text-[#ff2d78]" />
            Loading workspace team members...
          </div>
        ) : members.length === 0 ? (
          <div className="rounded-xl border border-dashed border-[#302840] p-8 text-center">
            <Users size={32} className="mx-auto text-[#64748b]" />
            <p className="mt-2 text-sm font-medium text-[#cbd5e1]">No team members found</p>
            <p className="mt-1 text-xs text-[#94a3b8]">Invite operators and viewers to collaborate on this workspace.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-[#28283c] text-[11px] font-bold uppercase tracking-wider text-[#94a3b8]">
                  <th className="pb-3 pr-4">User / Subject</th>
                  <th className="pb-3 pr-4">Assigned Role</th>
                  <th className="pb-3 pr-4">Status</th>
                  <th className="pb-3 pr-4">Joined / Activated</th>
                  <th className="pb-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#1e1e30]">
                {members.map((member) => {
                  const roleStyle = roleColor(member.role);
                  const statusStyle = statusBadge(member.status);
                  const RoleIcon = roleStyle.icon;
                  const isLastOwner = member.role === "owner" && members.filter((m) => m.role === "owner" && m.status === "active").length <= 1;

                  return (
                    <tr key={member.id} className="transition hover:bg-[#1e1e30]/40">
                      {/* Identity */}
                      <td className="py-3.5 pr-4">
                        <div className="flex items-center gap-2.5">
                          <div className="flex h-8 w-8 items-center justify-center rounded-lg border border-[#302840] bg-[#1e1e30] font-mono text-xs font-bold text-white">
                            {(member.user_id || "U").slice(0, 2).toUpperCase()}
                          </div>
                          <div>
                            <span className="font-mono text-xs text-white">
                              {member.user_id || "Pending Acceptance"}
                            </span>
                            <span className="block text-[10px] text-[#64748b]">
                              ID: {member.id}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Role */}
                      <td className="py-3.5 pr-4">
                        {isOwner && member.status === "active" ? (
                          <div className="relative inline-block">
                            <select
                              value={member.role}
                              disabled={actionLoading === member.user_id}
                              onChange={(e) => handleRoleChange(member.user_id!, e.target.value as TenantRole)}
                              className={`cursor-pointer rounded-lg border px-2.5 py-1 text-xs font-semibold uppercase tracking-wider transition ${roleStyle.border} ${roleStyle.bg} ${roleStyle.text} focus:outline-none focus:ring-1 focus:ring-[#ff2d78]`}
                            >
                              <option value="owner" className="bg-[#141422] text-[#ff2d78]">Owner</option>
                              <option value="operator" className="bg-[#141422] text-[#c084fc]">Operator</option>
                              <option value="viewer" className="bg-[#141422] text-[#00ffcc]">Viewer</option>
                            </select>
                          </div>
                        ) : (
                          <span className={`inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider ${roleStyle.border} ${roleStyle.bg} ${roleStyle.text}`}>
                            <RoleIcon size={12} />
                            {member.role}
                          </span>
                        )}
                      </td>

                      {/* Status */}
                      <td className="py-3.5 pr-4">
                        <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-medium ${statusStyle.bg}`}>
                          {statusStyle.label}
                        </span>
                      </td>

                      {/* Date */}
                      <td className="py-3.5 pr-4 font-mono text-[11px] text-[#94a3b8]">
                        {member.activated_at ? (
                          new Date(member.activated_at).toLocaleDateString("en-GB", {
                            day: "2-digit",
                            month: "short",
                            year: "numeric",
                          })
                        ) : (
                          <span className="flex items-center gap-1 text-amber-400">
                            <Clock size={11} />
                            Invited
                          </span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="py-3.5 text-right">
                        {isOwner && member.user_id && member.status === "active" ? (
                          isLastOwner ? (
                            <span className="text-[10px] text-[#64748b]" title="Last active owner cannot be revoked">
                              Last Owner
                            </span>
                          ) : (
                            <button
                              type="button"
                              onClick={() => setConfirmRevokeMember(member)}
                              disabled={actionLoading === member.user_id}
                              className="rounded p-1.5 text-rose-400 transition hover:bg-rose-500/10 hover:text-rose-300 disabled:opacity-50"
                              title="Revoke member access"
                            >
                              <Trash2 size={14} />
                            </button>
                          )
                        ) : (
                          <span className="text-[10px] text-[#64748b]">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Invite Member Modal */}
      {isInviteOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl border border-[#28283c] bg-[#141422] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-[#28283c] pb-4">
              <div className="flex items-center gap-2">
                <div className="rounded-lg border border-[#ff2d78]/30 bg-[#ff2d78]/10 p-2 text-[#ff2d78]">
                  <UserPlus size={18} />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Invite Team Member</h3>
                  <p className="text-xs text-[#94a3b8]">{activeTenant.name}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsInviteOpen(false)}
                className="rounded-lg p-1.5 text-[#94a3b8] hover:bg-[#1e1e30] hover:text-white"
              >
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleInvite} className="mt-5 space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#cbd5e1]">
                  Invitee Email Address <span className="text-[#ff2d78]">*</span>
                </label>
                <input
                  type="email"
                  required
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  placeholder="colleague@company.com"
                  className="mt-1.5 w-full rounded-xl border border-[#302840] bg-[#0c0c16] px-3.5 py-2.5 text-xs text-white placeholder-[#64748b] focus:border-[#ff2d78] focus:outline-none focus:ring-1 focus:ring-[#ff2d78]"
                />
                <p className="mt-1 text-[10px] text-[#94a3b8]">
                  Raw emails are not stored; an immutable SHA-256 subject digest is recorded for invitation acceptance.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#cbd5e1]">
                  Assigned Workspace Role <span className="text-[#ff2d78]">*</span>
                </label>
                <div className="mt-1.5 grid grid-cols-3 gap-2">
                  {(["viewer", "operator", "owner"] as TenantRole[]).map((r) => {
                    const isSelected = inviteRole === r;
                    const rStyle = roleColor(r);
                    return (
                      <button
                        key={r}
                        type="button"
                        onClick={() => setInviteRole(r)}
                        className={`rounded-xl border p-2.5 text-center text-xs font-bold uppercase transition ${
                          isSelected
                            ? `${rStyle.border} ${rStyle.bg} ${rStyle.text} ring-1 ring-[#ff2d78]/50`
                            : "border-[#302840] bg-[#0c0c16] text-[#94a3b8] hover:text-white"
                        }`}
                      >
                        {r}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#cbd5e1]">
                  Optional Known User ID
                </label>
                <input
                  type="text"
                  value={inviteUserId}
                  onChange={(e) => setInviteUserId(e.target.value)}
                  placeholder="usr-12345 (optional)"
                  className="mt-1.5 w-full rounded-xl border border-[#302840] bg-[#0c0c16] px-3.5 py-2.5 text-xs text-white placeholder-[#64748b] focus:border-[#ff2d78] focus:outline-none focus:ring-1 focus:ring-[#ff2d78]"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setIsInviteOpen(false)}
                  className="rounded-xl border border-[#302840] px-4 py-2.5 text-xs font-medium text-[#94a3b8] hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={inviting || !inviteEmail.trim()}
                  className="flex items-center gap-1.5 rounded-xl border border-[#ff2d78]/40 bg-[#ff2d78] px-4 py-2.5 text-xs font-bold text-white shadow-lg shadow-[#ff2d78]/25 transition hover:bg-[#ff2d78]/90 disabled:opacity-50"
                >
                  {inviting ? (
                    <>
                      <RefreshCw size={14} className="animate-spin" />
                      Creating Invite...
                    </>
                  ) : (
                    <>
                      <UserPlus size={14} />
                      Send Invite
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Revoke Confirmation Modal */}
      {confirmRevokeMember && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-2xl border border-rose-500/30 bg-[#141422] p-6 shadow-2xl">
            <div className="flex items-center gap-3 text-rose-400">
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-2.5">
                <Trash2 size={20} />
              </div>
              <h3 className="text-base font-bold text-white">Revoke Member Access</h3>
            </div>
            <p className="mt-3 text-xs leading-5 text-[#94a3b8]">
              Are you sure you want to revoke workspace access for user <span className="font-mono text-white">{confirmRevokeMember.user_id}</span>? They will immediately lose access to this tenant.
            </p>
            <div className="mt-5 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setConfirmRevokeMember(null)}
                className="rounded-xl border border-[#302840] px-3.5 py-2 text-xs font-medium text-[#94a3b8] hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={actionLoading === confirmRevokeMember.user_id}
                onClick={() => handleRevoke(confirmRevokeMember)}
                className="rounded-xl border border-rose-500/40 bg-rose-600 px-3.5 py-2 text-xs font-bold text-white shadow-lg shadow-rose-600/25 transition hover:bg-rose-500 disabled:opacity-50"
              >
                {actionLoading === confirmRevokeMember.user_id ? "Revoking..." : "Confirm Revoke"}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
