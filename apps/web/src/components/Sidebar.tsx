"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Phone,
  PhoneCall,
  Package,
  Truck,
  Boxes,
  Users,
  Calendar,
  MessageSquare,
  FileText,
  Zap,
  X,
  AlertTriangle,
  ChevronRight,
  ShieldCheck,
  LockKeyhole,
  ClipboardCheck,
  BarChart3,
  Gauge,
  Settings,
  Database,
} from "lucide-react";
import clsx from "clsx";

const NAV_GROUPS = [
  {
    label: "Main",
    items: [
      { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
      { href: "/dashboard/simulator", label: "Phone Simulator", icon: Phone },
      { href: "/dashboard/calls", label: "Calls", icon: PhoneCall },
      { href: "/dashboard/analytics", label: "Analytics", icon: BarChart3 },
      { href: "/dashboard/observability", label: "Observability", icon: Gauge },
      { href: "/dashboard/workspace", label: "Workspace Access", icon: ShieldCheck },
      { href: "/dashboard/privacy", label: "Privacy Controls", icon: LockKeyhole },
      { href: "/dashboard/readiness", label: "Pilot Readiness", icon: ClipboardCheck },
    ],
  },
  {
    label: "Operations",
    items: [
      { href: "/dashboard/data", label: "Data Hub & CSV", icon: Database },
      { href: "/dashboard/escalations", label: "Escalations", icon: AlertTriangle },
      { href: "/dashboard/orders", label: "Orders", icon: Package },
      { href: "/dashboard/shipments", label: "Shipments", icon: Truck },
      { href: "/dashboard/stock", label: "Stock", icon: Boxes },
      { href: "/dashboard/suppliers", label: "Suppliers", icon: Users },
      { href: "/dashboard/appointments", label: "Appointments", icon: Calendar },
      { href: "/dashboard/communications", label: "Outbound Logs", icon: MessageSquare },
    ],
  },

  {
    label: "Account",
    items: [
      { href: "/dashboard/settings", label: "Settings", icon: Settings },
    ],
  },
  {
    label: "External",
    items: [
      { href: "https://github.com/jeevesh2515/voxflow-voice-agent", label: "Docs", icon: FileText, external: true },
    ],
  },
];

type NavItem = {
  href: string;
  label: string;
  icon: any;
  external?: boolean;
};

export default function Sidebar({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const pathname = usePathname();

  return (
    <>
      {isOpen && <div className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm lg:hidden" onClick={onClose} />}

      <aside
        className={clsx(
          "w-[220px] bg-[#07070e]/95 border-r border-white/[0.06] flex flex-col hide-scrollbar overflow-y-auto shrink-0 select-none backdrop-blur-2xl",
          "fixed lg:static inset-y-0 left-0 z-40 transition-transform duration-200",
          isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        {/* Logo */}
        <div className="flex items-center justify-between px-5 pt-5 pb-3">
          <Link href="/dashboard" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-[#ff2d78]/15 border border-[#ff2d78]/30 flex items-center justify-center text-[#ff2d78] font-black text-sm shadow-[0_0_10px_rgba(255,45,120,0.2)]">
              V
            </div>
            <span className="text-base font-bold text-[#e8e0f0] tracking-tight">VoxFlow</span>
          </Link>
          <button onClick={onClose} className="p-1.5 text-[#a098b0] hover:text-[#e8e0f0] rounded-lg hover:bg-[#1e1e30] transition-colors lg:hidden">
            <X size={18} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-2 space-y-5 overflow-y-auto">
          {NAV_GROUPS.map((group) => (
            <div key={group.label}>
              <div className="px-3 mb-2">
                <span className="text-[9px] font-bold text-[#5a5068] uppercase tracking-[0.2em]">{group.label}</span>
              </div>
              <div className="space-y-0.5">
                {group.items.map((item: NavItem) => {
                  const Icon = item.icon;
                  const active = !item.external && pathname === item.href;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      target={item.external ? "_blank" : undefined}
                      onClick={onClose}
                      className={clsx(
                        "flex items-center gap-2.5 px-3 py-[7px] rounded-lg transition-all duration-150 text-[13px] group relative",
                        active
                          ? "bg-[#ff2d78]/10 text-[#ff2d78] font-semibold border border-[#ff2d78]/20 shadow-[0_0_12px_rgba(255,45,120,0.1)]"
                          : "text-[#94a3b8] hover:text-[#f8fafc] hover:bg-white/[0.04] border border-transparent"
                      )}
                    >
                      {active && <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-5 bg-[#ff2d78] rounded-full shadow-[0_0_8px_rgba(255,45,120,0.6)]" />}
                      <Icon size={16} className={clsx("shrink-0", active ? "text-[#ff2d78]" : "text-[#64748b] group-hover:text-[#f8fafc]")} />
                      <span className="flex-1 truncate">{item.label}</span>
                      {active && <ChevronRight size={12} className="text-[#ff2d78]/50" />}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="p-3 space-y-2.5 border-t border-white/[0.06]">
          <div className="rounded-xl border border-[#00ffcc]/15 bg-[#00ffcc]/[0.04] p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-bold text-[#64748b] uppercase tracking-[0.12em]">Queue</span>
              <span className="text-[10px] font-bold text-[#00ffcc]">OPTIMAL</span>
            </div>
            <div className="flex gap-1">
              {[1,2,3,4].map((i) => (<div key={i} className={`h-1 flex-1 rounded-full ${i <= 2 ? "bg-[#00ffcc] shadow-[0_0_6px_rgba(0,255,204,0.4)]" : "bg-white/[0.06]"}`} />))}
            </div>
          </div>
          <div className="flex items-center gap-2.5 px-1">
            <div className="w-7 h-7 rounded-lg bg-[#00ffcc]/10 border border-[#00ffcc]/15 grid place-items-center text-[#00ffcc]"><Zap size={13}/></div>
            <div><p className="text-[10px] font-bold tracking-widest uppercase text-[#64748b]">System</p><p className="text-xs font-bold text-[#00ffcc]">98.2% uptime</p></div>
          </div>
        </div>
      </aside>
    </>
  );
}
