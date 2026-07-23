"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  Search,
  CheckCircle2,
  ChevronDown,
  Plus,
  LogOut,
  User,
  Sun,
  Moon,
  Sparkles,
  Crown,
} from "lucide-react";
import { useTenant } from "@/lib/tenant-context";
import { useTheme } from "@/lib/theme-context";

export default function Topbar({ title, subtitle }: { title?: string; subtitle?: string }) {
  const router = useRouter();
  const { activeTenantId, activeTenant, tenants, setActiveTenantId, addTenant } = useTenant();
  const { theme, toggleTheme } = useTheme();

  const [isAddingTenant, setIsAddingTenant] = useState(false);
  const [newCompanyName, setNewCompanyName] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const handleAddCompanySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCompanyName.trim()) return;
    const created = addTenant(newCompanyName);
    setNewCompanyName("");
    setIsAddingTenant(false);
    setActiveTenantId(created.id);
  };

  const handleLogout = () => {
    localStorage.removeItem("voxflow_session");
    router.push("/sign-in");
  };

  return (
    <nav className="w-full z-50 bg-[#0a0a12]/90 dark:bg-[#0a0a12]/95 light:bg-white/95 backdrop-blur-md border-b border-[#ff2d78]/20 dark:border-[#ff2d78]/20 light:border-slate-200 shadow-sm px-6 py-3 flex justify-between items-center shrink-0 transition-colors duration-300">
      <div className="flex items-center gap-6 lg:gap-8">
        {/* Brand Logo */}
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[#ff2d78]/20 border border-[#ff2d78]/40 flex items-center justify-center text-[#ff2d78] font-black font-headline text-lg shadow-[0_0_12px_rgba(255,45,120,0.4)]">
            V
          </div>
          <span className="text-xl lg:text-2xl font-headline font-black tracking-tighter text-[#e8e0f0] dark:text-[#e8e0f0] light:text-slate-900">
            VoxFlow
          </span>
        </Link>

        {/* Company Selector Dropdown & Add Action */}
        <div className="hidden sm:flex items-center gap-3">
          {isAddingTenant ? (
            <form onSubmit={handleAddCompanySubmit} className="flex items-center gap-1.5 bg-[#1e1e30] dark:bg-[#1e1e30] light:bg-slate-100 border border-[#ff2d78] rounded-xl px-3 py-1.5">
              <input
                type="text"
                autoFocus
                value={newCompanyName}
                onChange={(e) => setNewCompanyName(e.target.value)}
                placeholder="Company Name..."
                className="bg-transparent text-xs text-[#e8e0f0] dark:text-[#e8e0f0] light:text-slate-900 placeholder:text-[#a098b0]/50 focus:outline-none w-36 font-body"
              />
              <button
                type="submit"
                className="bg-[#ff2d78] text-[#1a0010] font-headline font-bold text-[10px] uppercase px-2 py-1 rounded-md"
              >
                Add
              </button>
              <button
                type="button"
                onClick={() => setIsAddingTenant(false)}
                className="text-[#a098b0] hover:text-[#e8e0f0] text-xs px-1"
              >
                ✕
              </button>
            </form>
          ) : (
            <div className="flex items-center gap-3 bg-[#1e1e30]/60 dark:bg-[#1e1e30]/60 light:bg-slate-100/80 backdrop-blur-sm px-3.5 py-1.5 rounded-xl border border-[#302840]/60 dark:border-[#302840]/60 light:border-slate-300 hover:border-[#ff2d78]/50 transition-all group">
              <div className="w-8 h-8 rounded-lg bg-[#ff2d78]/20 flex items-center justify-center text-[#ff2d78] font-bold text-xs border border-[#ff2d78]/30 shadow-[0_0_10px_rgba(255,45,120,0.2)] shrink-0">
                {activeTenant.name.charAt(0).toUpperCase()}
              </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-1.5">
                  <select
                    value={activeTenantId}
                    onChange={(e) => setActiveTenantId(e.target.value)}
                    className="bg-transparent text-xs font-headline font-bold text-[#e8e0f0] dark:text-[#e8e0f0] light:text-slate-900 focus:outline-none cursor-pointer pr-1 max-w-[170px] truncate"
                  >
                    {tenants.map((t) => (
                      <option key={t.id} value={t.id} className="bg-[#141422] dark:bg-[#141422] light:bg-white text-[#e8e0f0] dark:text-[#e8e0f0] light:text-slate-900">
                        {t.name}
                      </option>
                    ))}
                  </select>
                  <CheckCircle2 size={13} className="text-[#00ffcc] dark:text-[#00ffcc] light:text-teal-600 shrink-0" />
                </div>
                <div className="flex items-center gap-2 text-[9px] font-label text-[#a098b0] dark:text-[#a098b0] light:text-slate-500 uppercase tracking-wider">
                  <span>12 Active Agents</span>
                  <span>·</span>
                  <span className="flex items-center gap-1 text-[#00ffcc] dark:text-[#00ffcc] light:text-teal-600 font-bold">
                    <span className="w-1 h-1 rounded-full bg-[#00ffcc] dark:bg-[#00ffcc] light:bg-teal-600 animate-ping" />
                    99.9% Uptime
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsAddingTenant(true)}
                title="Add New Workspace"
                className="text-[#ff2d78] hover:text-[#ff2d78]/80 p-1 rounded hover:bg-[#ff2d78]/10 ml-1 transition-colors"
              >
                <Plus size={14} />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3 lg:gap-5">
        {/* Subscription Plan Quota Badge */}
        <div className="hidden xl:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-[#141422] dark:bg-[#141422] light:bg-slate-100 border border-[#00ffcc]/30 dark:border-[#00ffcc]/30 light:border-teal-300 text-xs font-label">
          <Crown size={14} className="text-[#ffe04a] shrink-0" />
          <span className="text-[#e8e0f0] dark:text-[#e8e0f0] light:text-slate-900 font-semibold">Pro Plan</span>
          <span className="text-[#a098b0] dark:text-[#a098b0] light:text-slate-500">1,242 / 1,500 calls</span>
          <Link href="/pricing" className="text-[10px] uppercase font-bold text-[#00ffcc] dark:text-[#00ffcc] light:text-teal-600 hover:underline ml-1">
            Upgrade
          </Link>
        </div>

        {/* Light / Dark Mode Toggle */}
        <button
          type="button"
          onClick={toggleTheme}
          title={`Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`}
          className="p-2 rounded-xl bg-[#1e1e30] dark:bg-[#1e1e30] light:bg-slate-100 border border-[#302840] dark:border-[#302840] light:border-slate-300 text-[#e8e0f0] dark:text-[#ffe04a] light:text-slate-700 hover:scale-105 active:scale-95 transition-all shadow-sm"
        >
          {theme === "dark" ? <Sun size={17} className="text-[#ffe04a]" /> : <Moon size={17} className="text-slate-700" />}
        </button>

        {/* Search Bar */}
        <div className="relative hidden lg:block group">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#a098b0] group-focus-within:text-[#ff2d78] transition-colors" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && searchQuery.trim()) router.push(`/dashboard/calls?q=${encodeURIComponent(searchQuery.trim())}`); }}
            placeholder="Search agents, calls..."
            className="bg-[#0a0a12] dark:bg-[#0a0a12] light:bg-slate-50 border border-[#302840] dark:border-[#302840] light:border-slate-300 rounded-xl pl-9 pr-12 py-2 text-xs text-[#e8e0f0] dark:text-[#e8e0f0] light:text-slate-900 focus:ring-1 focus:ring-[#ff2d78] outline-none w-56 lg:w-64 transition-all placeholder:text-[#a098b0]/50 font-body"
          />
        </div>

        {/* Pilot CTA Button */}
        <Link
          href="/sign-up"
          className="bg-[#b3004e] text-[#ffe0ec] px-4 py-2 rounded-full font-label text-xs font-bold uppercase tracking-widest hover:scale-105 active:scale-95 transition-all shadow-[0_0_15px_rgba(255,45,120,0.3)] hidden sm:inline-block"
        >
          Request Pilot
        </Link>

        {/* User Profile & Logout */}
        <div className="flex items-center gap-2 border-l border-[#302840] dark:border-[#302840] light:border-slate-300 pl-3 sm:pl-4">
          <div className="w-8 h-8 rounded-full bg-[#1e1e30] dark:bg-[#1e1e30] light:bg-slate-200 border border-[#302840] dark:border-[#302840] light:border-slate-300 flex items-center justify-center text-[#00ffcc] dark:text-[#00ffcc] light:text-teal-600">
            <User size={15} />
          </div>
          <button
            onClick={handleLogout}
            title="Sign Out"
            className="p-1.5 text-[#a098b0] hover:text-[#ff2d78] hover:bg-[#1e1e30] rounded-lg transition-colors"
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </nav>
  );
}
