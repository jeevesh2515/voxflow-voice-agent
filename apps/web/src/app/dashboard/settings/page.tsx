"use client";

import { Globe2, Palette, Settings2 } from "lucide-react";
import AgentSettings from "@/components/settings/AgentSettings";
import GoogleSheetsSettings from "@/components/settings/GoogleSheetsSettings";
import TeamMembersSettings from "@/components/settings/TeamMembersSettings";
import TelephonySettings from "@/components/settings/TelephonySettings";
import { useTenant } from "@/lib/tenant-context";
import { useTheme } from "@/lib/theme-context";

function titleCase(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export default function SettingsPage() {
  const { activeTenant, tenants, setActiveTenantId, demoMode } = useTenant();
  const { theme, setTheme } = useTheme();
  const nextTheme = theme === "dark" ? "light" : "dark";

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-16">
      <header className="rounded-2xl border border-[#28283c] bg-[#141422] p-5 sm:p-6">
        <div className="flex items-start gap-3">
          <div className="rounded-xl border border-[#ff2d78]/25 bg-[#ff2d78]/10 p-2.5 text-[#ff2d78]">
            <Settings2 size={20} />
          </div>
          <div>
            <p className="text-xs font-mono text-[#94a3b8]">Workspace settings / {activeTenant.name}</p>
            <h1 className="mt-1 text-2xl font-bold text-white">Settings</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-[#94a3b8]">
              Configure agent persona demeanor, operating hours, and fallback policies, manage team member roles and permissions, review server-authoritative telephony controls, and adjust local workspace appearance. Administrative mutations are restricted to workspace owners.
            </p>
          </div>
        </div>
      </header>

      <TeamMembersSettings />

      <AgentSettings />

      <GoogleSheetsSettings />

      <TelephonySettings />

      <section className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.6fr)]">
        <div className="overflow-hidden rounded-2xl border border-[#302840]/60 bg-[#141422]/40">
          <div className="flex items-center gap-3 border-b border-[#302840]/40 bg-[#0f0f1a]/60 px-5 py-4 sm:px-6">
            <Globe2 size={18} className="text-[#00ffcc]" />
            <div>
              <h2 className="text-sm font-bold text-[#e8e0f0]">Workspace</h2>
              <p className="text-[10px] text-[#a098b0]">Switch between server-authorized companies</p>
            </div>
          </div>
          <div className="p-5 sm:p-6">
            <div className="flex flex-wrap gap-2" aria-label="Authorized workspaces">
              {tenants.map((tenant) => {
                const isActive = tenant.id === activeTenant.id;
                return (
                  <button
                    key={tenant.id}
                    type="button"
                    aria-pressed={isActive}
                    onClick={() => setActiveTenantId(tenant.id)}
                    className={`rounded-lg border px-3 py-2 text-left text-xs font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff2d78]/50 ${
                      isActive
                        ? "border-[#ff2d78]/35 bg-[#ff2d78]/10 text-[#ff8db5]"
                        : "border-[#302840] bg-[#1e1e30] text-[#a098b0] hover:border-[#ff2d78]/30 hover:text-white"
                    }`}
                  >
                    <span className="block">{tenant.name}</span>
                    <span className="mt-0.5 block text-[9px] font-mono uppercase tracking-wider opacity-70">{demoMode ? "Demo" : titleCase(tenant.role)}</span>
                  </button>
                );
              })}
            </div>
            {tenants.length === 0 && <p className="text-sm text-[#a098b0]">No authorized workspaces are available.</p>}
            <p className="mt-4 rounded-lg border border-[#00ffcc]/20 bg-[#00ffcc]/5 px-3 py-2 text-xs leading-5 text-[#a098b0]">
              Workspaces are granted through server-authorized memberships. Selecting a workspace changes the tenant-scoped settings loaded above; it does not grant additional access.
            </p>
          </div>
        </div>

        <div className="overflow-hidden rounded-2xl border border-[#302840]/60 bg-[#141422]/40">
          <div className="flex items-center gap-3 border-b border-[#302840]/40 bg-[#0f0f1a]/60 px-5 py-4 sm:px-6">
            <Palette size={18} className="text-[#ff2d78]" />
            <div>
              <h2 className="text-sm font-bold text-[#e8e0f0]">Appearance</h2>
              <p className="text-[10px] text-[#a098b0]">Local dashboard theme</p>
            </div>
          </div>
          <div className="p-5 sm:p-6">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-medium text-[#e8e0f0]">{titleCase(theme)} mode</p>
                <p className="mt-1 text-[10px] leading-4 text-[#a098b0]">This preference is stored in this browser.</p>
              </div>
              <button
                type="button"
                onClick={() => setTheme(nextTheme)}
                className="shrink-0 rounded-lg border border-[#302840] bg-[#1e1e30] px-3 py-2 text-xs font-semibold text-[#e8e0f0] transition hover:border-[#ff2d78]/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#ff2d78]/50"
              >
                Use {nextTheme}
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
