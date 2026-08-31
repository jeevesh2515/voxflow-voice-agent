"use client";

import { useState, useEffect } from "react";
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
  const [now, setNow] = useState<string>("");
  useEffect(() => {
    const t = () => setNow(new Date().toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/London" }) + " GMT");
    t(); const id = setInterval(t, 60000); return () => clearInterval(id);
  }, []);
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
    <nav className="w-full z-50 bg-[#07070e]/90 backdrop-blur-2xl border-b border-white/[0.06] px-4 sm:px-5 py-2.5 flex justify-between items-center shrink-0">
      <div className="flex items-center gap-3 lg:gap-5">
        <button onClick={onToggleSidebar} className="p-2 lg:hidden text-[#94a3b8] hover:text-white hover:bg-white/[0.06] rounded-xl transition-colors" aria-label="Toggle sidebar"><Menu size={18} /></button>
        <Link href="/dashboard" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[#ff2d78] to-[#ff5996] flex items-center justify-center text-white font-black text-base shadow-[0_0_16px_rgba(255,45,120,0.3)]">V</div>
          <span className="text-lg font-black tracking-tight text-[#f8fafc] hidden sm:inline">VoxFlow</span>
          <span className="hidden lg:inline-flex items-center gap-1.5 rounded-full border border-[#00ffcc]/20 bg-[#00ffcc]/10 px-2.5 py-1 text-[10px] font-bold tracking-widest uppercase text-[#00ffcc]"><span className="w-1.5 h-1.5 rounded-full bg-[#00ffcc] animate-pulse"/>All Systems Operational <span className="hidden xl:inline">in London eu-west-2</span></span>
        </Link>
        <div className="hidden sm:flex items-center gap-3">
          <div className="flex items-center gap-3 bg-[#0f0f1c]/80 backdrop-blur-xl px-3 py-1.5 rounded-xl border border-white/[0.07] shadow-sm">
            <div className="w-7 h-7 rounded-lg bg-[#ff2d78]/15 flex items-center justify-center text-[#ff2d78] font-bold text-xs border border-[#ff2d78]/20 shrink-0">{activeTenant?.name ? activeTenant.name.charAt(0).toUpperCase() : "W"}</div>
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5">
                <select value={activeTenantId} onChange={(e) => setActiveTenantId(e.target.value)} disabled={tenantLoading || !tenants.length} className="bg-transparent text-xs font-bold text-[#f8fafc] focus:outline-none cursor-pointer pr-1 max-w-[160px] truncate disabled:cursor-not-allowed">
                  {tenants.length ? tenants.map((tenant) => (<option key={tenant.id} value={tenant.id} className="bg-[#0f0f1c] text-[#f8fafc]">{tenant.name}</option>)) : <option value="">{tenantLoading ? "Loading…" : "No workspace"}</option>}
                </select>
                {tenants.length > 0 && <CheckCircle2 size={12} className="text-[#00ffcc] shrink-0" />}
              </div>
              <span className={`flex items-center gap-1 text-[10px] font-mono uppercase tracking-wider font-semibold ${demoMode ? "text-[#f59e0b]" : "text-[#00ffcc]"}`}><span className={`w-1 h-1 rounded-full ${demoMode ? "bg-[#f59e0b]" : "bg-[#00ffcc]"}`} />{demoMode ? "Read-only demo" : `${activeTenant.role} · ${activeTenantId.slice(0,6)}`}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 lg:gap-3">
        <div className="relative hidden md:block group">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#64748b] group-focus-within:text-[#ff2d78] transition-colors" />
          <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && searchQuery.trim()) router.push(`/dashboard/calls?q=${encodeURIComponent(searchQuery.trim())}`); }} placeholder="Search orders, calls, SKUs…" className="bg-[#0f0f1c]/80 border border-white/[0.07] rounded-xl pl-8 pr-3 py-1.5 text-xs text-[#f8fafc] focus:border-[#ff2d78]/40 outline-none w-44 lg:w-52 transition-all placeholder:text-[#64748b]" />
        </div>

        {now && <span className="hidden lg:inline-flex items-center gap-1.5 text-[11px] font-mono text-[#94a3b8] border border-white/[0.06] bg-white/[0.03] px-2.5 py-1 rounded-full">{now}</span>}
        <Link href="/dashboard/simulator" className="hidden sm:inline-flex items-center gap-1.5 bg-[#ff2d78] hover:bg-[#e02669] text-white px-3 py-1.5 rounded-xl text-xs font-bold shadow-[0_0_16px_rgba(255,45,120,0.25)] active:scale-95 transition-all"><Phone size={12}/><span>Simulator</span></Link>
        <div className="flex items-center gap-1.5 border-l border-white/[0.06] pl-2.5">
          <div className="w-7 h-7 rounded-lg bg-white/[0.06] border border-white/[0.07] grid place-items-center text-[#00ffcc]"><User size={13}/></div>
          <button onClick={handleLogout} title="Sign Out" className="p-1.5 text-[#94a3b8] hover:text-[#ff2d78] hover:bg-white/[0.06] rounded-lg transition-colors"><LogOut size={14}/></button>
        </div>
      </div>
    </nav>
  );
}
