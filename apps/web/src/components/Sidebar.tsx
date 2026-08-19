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
} from "lucide-react";
import clsx from "clsx";

const NAV_GROUPS = [
  {
    label: "Main",
    items: [
      { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
      { href: "/dashboard/simulator", label: "Phone Simulator", icon: Phone },
      { href: "/dashboard/calls", label: "Calls", icon: PhoneCall },
    ],
  },
  {
    label: "Operations",
    items: [
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
          "w-60 bg-[#111118]/95 border-r border-[#302840]/60 flex flex-col hide-scrollbar overflow-y-auto shrink-0 select-none backdrop-blur-xl",
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
                        "flex items-center gap-3 px-3 py-2 rounded-xl transition-all duration-150 text-sm group",
                        active
                          ? "bg-[#ff2d78]/10 text-[#ff2d78] font-semibold border border-[#ff2d78]/20 shadow-[0_0_12px_rgba(255,45,120,0.08)]"
                          : "text-[#a098b0] hover:text-[#e8e0f0] hover:bg-[#1e1e30]/50"
                      )}
                    >
                      <Icon size={18} className={clsx("shrink-0", active ? "text-[#ff2d78]" : "text-[#a098b0] group-hover:text-[#e8e0f0]")} />
                      <span className="flex-1">{item.label}</span>
                      {active && <ChevronRight size={14} className="text-[#ff2d78]/60" />}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Bottom Status */}
        <div className="p-4 space-y-2.5 border-t border-[#302840]/40">
          <div className="rounded-xl border border-[#00ffcc]/15 bg-[#00ffcc]/5 p-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[9px] font-bold text-[#a098b0] uppercase tracking-widest">Queue</span>
              <span className="text-[9px] font-bold text-[#00ffcc]">OPTIMAL</span>
            </div>
            <div className="flex gap-1">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className={`h-1 flex-1 rounded-full ${i <= 2 ? "bg-[#00ffcc] shadow-[0_0_6px_rgba(0,255,204,0.4)]" : "bg-[#302840]"}`} />
              ))}
            </div>
          </div>

          <div className="flex items-center gap-3 px-2">
            <div className="w-8 h-8 rounded-lg bg-[#00ffcc]/10 border border-[#00ffcc]/20 flex items-center justify-center text-[#00ffcc]">
              <Zap size={14} />
            </div>
            <div>
              <p className="text-[9px] text-[#a098b0] uppercase tracking-wider font-bold">System</p>
              <p className="text-xs font-bold text-[#00ffcc]">98.2% uptime</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
