"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Search,
  Menu,
  CheckCircle2,
  ChevronDown,
  LogOut,
  User,
  Sun,
  Moon,
  Sparkles,
  Crown,
  Phone,
  Radio,
} from "lucide-react";
import { useTenant } from "@/lib/tenant-context";
import { useTheme } from "@/lib/theme-context";
import { createClient } from "@/lib/supabase/client";

export default function Topbar({ title, subtitle, onToggleSidebar }: { title?: string; subtitle?: string; onToggleSidebar?: () => void }) {
  const router = useRouter();
  const { activeTenantId, activeTenant, tenants, loading: tenantLoading, demoMode, setActiveTenantId } = useTenant();
  const { theme, toggleTheme } = useTheme();

  const [searchQuery, setSearchQuery] = useState("");

  const handleLogout = async () => {
    try {
      const supabase = createClient();
      await supabase.auth.signOut();
    } catch (e) {
      console.warn("Sign out exception:", e);
    }
    localStorage.removeItem("voxflow_session");
    localStorage.removeItem("voxflow_demo_user");
    router.push("/sign-in");
  };

  return (
    <nav className="w-full z-50 bg-[#0d0d16]/95 backdrop-blur-md border-b border-[#242436] px-5 py-3 flex justify-between items-center shrink-0 transition-colors">
      <div className="flex items-center gap-3 lg:gap-6">
        {/* Mobile menu toggle */}
        <button
          onClick={onToggleSidebar}
          className="p-2 lg:hidden text-[#94a3b8] hover:text-[#f1f5f9] hover:bg-[#1e1e30] rounded-xl transition-colors"
          aria-label="Toggle sidebar"
        >
          <Menu size={20} />
        </button>

        {/* Brand Logo */}
        <Link href="/dashboard" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[#ff2d78] to-[#ff5996] flex items-center justify-center text-white font-black font-headline text-base shadow-md">
            V
          </div>
          <div className="flex flex-col">
            <span className="text-lg lg:text-xl font-headline font-black tracking-tight text-[#ffffff]">
              VoxFlow
            </span>
          </div>
        </Link>

        {/* Server-authorized workspace selector */}
        <div className="hidden sm:flex items-center gap-3">
          <div className="flex items-center gap-3 bg-[#141422] px-3.5 py-1.5 rounded-xl border border-[#28283c] shadow-sm">
            <div className="w-7 h-7 rounded-lg bg-[#ff2d78]/20 flex items-center justify-center text-[#ff2d78] font-bold text-xs border border-[#ff2d78]/30 shrink-0">
              {activeTenant?.name ? activeTenant.name.charAt(0).toUpperCase() : "W"}
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5">
                <select
                  value={activeTenantId}
                  onChange={(e) => setActiveTenantId(e.target.value)}
                  disabled={tenantLoading || !tenants.length}
                  className="bg-transparent text-xs font-headline font-bold text-[#f1f5f9] focus:outline-none cursor-pointer pr-1 max-w-[180px] truncate disabled:cursor-not-allowed"
                >
                  {tenants.length ? tenants.map((tenant) => (
                    <option key={tenant.id} value={tenant.id} className="bg-[#141422] text-[#f1f5f9]">
                      {tenant.name}
                    </option>
                  )) : <option value="">{tenantLoading ? "Loading workspaces…" : "No authorized workspace"}</option>}
                </select>
                {tenants.length > 0 && <CheckCircle2 size={13} className="text-[#00ffcc] shrink-0" />}
              </div>
              <div className="flex items-center gap-1.5 text-[9px] font-label text-[#94a3b8] uppercase tracking-wider font-semibold">
                <span className={`flex items-center gap-1 font-bold ${demoMode ? "text-[#ffe04a]" : "text-[#00ffcc]"}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${demoMode ? "bg-[#ffe04a]" : "bg-[#00ffcc]"}`} />
                  {demoMode ? "Read-only demo" : `${activeTenant.role} access`}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3 lg:gap-4">
        {/* Search Bar */}
        <div className="relative hidden md:block group">
          <Search size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#64748b] group-focus-within:text-[#ff2d78] transition-colors" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && searchQuery.trim()) router.push(`/dashboard/calls?q=${encodeURIComponent(searchQuery.trim())}`); }}
            placeholder="Search orders, calls, SKUs..."
            className="bg-[#141420] border border-[#28283c] rounded-xl pl-9 pr-4 py-1.5 text-xs text-[#f1f5f9] focus:border-[#ff2d78] outline-none w-48 lg:w-56 transition-all placeholder:text-[#64748b] font-body"
          />
        </div>

        {/* Quick Simulator CTA Button */}
        <Link
          href="/dashboard/simulator"
          className="flex items-center gap-2 bg-[#ff2d78] hover:bg-[#e02669] text-white px-3.5 py-1.5 rounded-xl font-label text-xs font-bold transition-all shadow-md active:scale-95"
        >
          <Phone size={13} />
          <span>Voice Simulator</span>
        </Link>

        {/* User Profile & Logout */}
        <div className="flex items-center gap-2 border-l border-[#242436] pl-3">
          <div className="w-8 h-8 rounded-xl bg-[#181826] border border-[#28283c] flex items-center justify-center text-[#00ffcc]">
            <User size={15} />
          </div>
          <button
            onClick={handleLogout}
            title="Sign Out"
            className="p-2 text-[#94a3b8] hover:text-[#ff2d78] hover:bg-[#181826] rounded-xl transition-colors"
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </nav>
  );
}
