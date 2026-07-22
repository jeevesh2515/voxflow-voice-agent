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
  Zap,
} from "lucide-react";
import { useTenant } from "@/lib/tenant-context";

export default function Topbar({ title, subtitle }: { title?: string; subtitle?: string }) {
  const router = useRouter();
  const { activeTenantId, activeTenant, tenants, setActiveTenantId, addTenant } = useTenant();

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
    <nav className="w-full z-50 bg-[#0a0a12]/90 backdrop-blur-md border-b border-[#ff2d78]/20 shadow-[0_0_20px_rgba(255,45,120,0.1)] px-6 py-3.5 flex justify-between items-center shrink-0">
      <div className="flex items-center gap-6 lg:gap-10">
        {/* Brand Logo */}
        <Link href="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[#ff2d78]/20 border border-[#ff2d78]/40 flex items-center justify-center text-[#ff2d78] font-black font-headline text-lg shadow-[0_0_12px_rgba(255,45,120,0.4)]">
            V
          </div>
          <span className="text-xl lg:text-2xl font-headline font-black tracking-tighter text-[#e8e0f0]">
            VoxFlow
          </span>
        </Link>

        {/* Company Selector Dropdown & Add Action */}
        <div className="hidden sm:flex items-center gap-3">
          {isAddingTenant ? (
            <form onSubmit={handleAddCompanySubmit} className="flex items-center gap-1.5 bg-[#1e1e30] border border-[#ff2d78] rounded-xl px-3 py-1.5">
              <input
                type="text"
                autoFocus
                value={newCompanyName}
                onChange={(e) => setNewCompanyName(e.target.value)}
                placeholder="Company Name..."
                className="bg-transparent text-xs text-[#e8e0f0] placeholder:text-[#a098b0]/50 focus:outline-none w-36 font-body"
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
            <div className="flex items-center gap-3 bg-[#1e1e30]/60 backdrop-blur-sm px-3.5 py-1.5 rounded-xl border border-[#302840]/60 hover:border-[#ff2d78]/50 transition-all group">
              <div className="w-8 h-8 rounded-lg bg-[#ff2d78]/20 flex items-center justify-center text-[#ff2d78] font-bold text-xs border border-[#ff2d78]/30 shadow-[0_0_10px_rgba(255,45,120,0.2)] shrink-0">
                {activeTenant.name.charAt(0).toUpperCase()}
              </div>
              <div className="flex flex-col">
                <div className="flex items-center gap-1.5">
                  <select
                    value={activeTenantId}
                    onChange={(e) => setActiveTenantId(e.target.value)}
                    className="bg-transparent text-xs font-headline font-bold text-[#e8e0f0] focus:outline-none cursor-pointer pr-1 max-w-[170px] truncate"
                  >
                    {tenants.map((t) => (
                      <option key={t.id} value={t.id} className="bg-[#141422] text-[#e8e0f0]">
                        {t.name}
                      </option>
                    ))}
                  </select>
                  <CheckCircle2 size={13} className="text-[#00ffcc] shrink-0" />
                </div>
                <div className="flex items-center gap-2 text-[9px] font-label text-[#a098b0] uppercase tracking-wider">
                  <span>12 Active Agents</span>
                  <span className="text-[#302840]">·</span>
                  <span className="flex items-center gap-1 text-[#00ffcc] font-bold">
                    <span className="w-1 h-1 rounded-full bg-[#00ffcc] animate-ping" />
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
      <div className="flex items-center gap-4 lg:gap-6">
        {/* Search Bar */}
        <div className="relative hidden md:block group">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#a098b0] group-focus-within:text-[#ff2d78] transition-colors" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search agents, calls, or logs..."
            className="bg-[#0a0a12] border border-[#302840] rounded-xl pl-10 pr-14 py-2 text-xs text-[#e8e0f0] focus:ring-1 focus:ring-[#ff2d78] focus:border-[#ff2d78] outline-none w-64 lg:w-72 transition-all placeholder:text-[#a098b0]/50 font-body"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2 flex gap-1 pointer-events-none">
            <kbd className="px-1.5 py-0.5 rounded bg-[#1e1e30] border border-[#302840] text-[9px] font-label text-[#a098b0]">⌘</kbd>
            <kbd className="px-1.5 py-0.5 rounded bg-[#1e1e30] border border-[#302840] text-[9px] font-label text-[#a098b0]">K</kbd>
          </div>
        </div>

        {/* Pilot CTA Button */}
        <Link
          href="/sign-up"
          className="bg-[#b3004e] text-[#ffe0ec] px-4 py-2 rounded-full font-label text-xs font-bold uppercase tracking-widest hover:scale-105 active:scale-95 transition-all shadow-[0_0_15px_rgba(255,45,120,0.3)] hidden sm:inline-block"
        >
          Request Pilot
        </Link>

        {/* User Profile & Logout */}
        <div className="flex items-center gap-2 border-l border-[#302840] pl-4 sm:pl-6">
          <div className="w-8 h-8 rounded-full bg-[#1e1e30] border border-[#302840] flex items-center justify-center text-[#00ffcc]">
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
