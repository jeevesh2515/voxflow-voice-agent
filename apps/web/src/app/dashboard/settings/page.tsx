"use client";

import { useState } from "react";
import { Bell, User, Shield, Palette, Globe, Volume2, Save } from "lucide-react";
import { useTenant } from "@/lib/tenant-context";
import { useTheme } from "@/lib/theme-context";

export default function SettingsPage() {
  const { activeTenant, tenants, setActiveTenantId } = useTenant();
  const { theme, setTheme } = useTheme();
  const [saving, setSaving] = useState(false);
  const [notifications, setNotifications] = useState({
    email: true,
    whatsapp: true,
    escalation: true,
    daily: false,
  });

  const handleSave = () => {
    setSaving(true);
    setTimeout(() => setSaving(false), 800);
  };

  return (
    <div className="space-y-6">
      <div className="px-6 pt-6 pb-2">
        <h1 className="text-xl font-bold text-[#e8e0f0]">Settings</h1>
        <p className="text-xs text-[#a098b0] mt-1">Manage your workspace preferences</p>
      </div>

      <div className="px-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Workspace */}
        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-2xl border border-[#302840]/60 bg-[#141422]/40 overflow-hidden">
            <div className="px-6 py-4 border-b border-[#302840]/40 flex items-center gap-3">
              <Globe size={18} className="text-[#00ffcc]" />
              <div>
                <h3 className="font-bold text-[#e8e0f0] text-sm">Workspace</h3>
                <p className="text-[10px] text-[#a098b0]">Manage your companies</p>
              </div>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex flex-wrap gap-2">
                {tenants.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setActiveTenantId(t.id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                      t.id === activeTenant?.id
                        ? "bg-[#ff2d78]/10 border-[#ff2d78]/30 text-[#ff2d78]"
                        : "bg-[#1e1e30] border-[#302840] text-[#a098b0] hover:border-[#ff2d78]/30"
                    }`}
                  >
                    {t.name}
                  </button>
                ))}
              </div>
              <p className="rounded-lg border border-[#00ffcc]/20 bg-[#00ffcc]/5 px-3 py-2 text-xs text-[#a098b0]">Workspaces are granted through server-authorized memberships. An owner can invite approved users from Workspace Access.</p>
            </div>
          </div>

          <div className="rounded-2xl border border-[#302840]/60 bg-[#141422]/40 overflow-hidden">
            <div className="px-6 py-4 border-b border-[#302840]/40 flex items-center gap-3">
              <Bell size={18} className="text-[#ffe04a]" />
              <div>
                <h3 className="font-bold text-[#e8e0f0] text-sm">Notifications</h3>
                <p className="text-[10px] text-[#a098b0]">Configure alert preferences</p>
              </div>
            </div>
            <div className="p-6 space-y-4">
              {Object.entries(notifications).map(([key, val]) => (
                <div key={key} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-[#e8e0f0] capitalize">{key}</p>
                    <p className="text-[10px] text-[#a098b0]">Receive {key} notifications</p>
                  </div>
                  <button
                    onClick={() => setNotifications((prev) => ({ ...prev, [key]: !val }))}
                    className={`w-10 h-6 rounded-full transition-colors relative ${val ? "bg-[#00ffcc]" : "bg-[#302840]"}`}
                  >
                    <div className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${val ? "translate-x-5" : "translate-x-1"}`} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <div className="rounded-2xl border border-[#302840]/60 bg-[#141422]/40 overflow-hidden">
            <div className="px-6 py-4 border-b border-[#302840]/40 flex items-center gap-3">
              <Palette size={18} className="text-[#ff2d78]" />
              <div>
                <h3 className="font-bold text-[#e8e0f0] text-sm">Appearance</h3>
                <p className="text-[10px] text-[#a098b0]">Theme settings</p>
              </div>
            </div>
            <div className="p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-[#e8e0f0]">Dark Mode</p>
                  <p className="text-[10px] text-[#a098b0]">Current: {theme}</p>
                </div>
                <button
                  onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                  className="px-3 py-1.5 rounded-lg bg-[#1e1e30] border border-[#302840] text-xs text-[#e8e0f0] hover:border-[#ff2d78] transition-all"
                >
                  Toggle
                </button>
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-[#302840]/60 bg-[#141422]/40 overflow-hidden">
            <div className="px-6 py-4 border-b border-[#302840]/40 flex items-center gap-3">
              <Shield size={18} className="text-[#00ffcc]" />
              <div>
                <h3 className="font-bold text-[#e8e0f0] text-sm">Security</h3>
                <p className="text-[10px] text-[#a098b0]">Account settings</p>
              </div>
            </div>
            <div className="p-6">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-[#1e1e30] border border-[#302840] flex items-center justify-center text-[#00ffcc]">
                  <User size={18} />
                </div>
                <div>
                  <p className="text-sm font-medium text-[#e8e0f0]">{activeTenant?.name || "User"}</p>
                  <p className="text-[10px] text-[#a098b0] font-mono">admin@voxflow.ai</p>
                </div>
              </div>
            </div>
          </div>

          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full py-3 rounded-xl bg-[#ff2d78] text-[#1a0010] font-bold text-sm hover:scale-[1.02] active:scale-[0.98] transition-all shadow-[0_0_16px_rgba(255,45,120,0.3)] flex items-center justify-center gap-2"
          >
            {saving ? (
              <div className="w-4 h-4 border-2 border-[#1a0010] border-t-transparent rounded-full animate-spin" />
            ) : (
              <Save size={16} />
            )}
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
