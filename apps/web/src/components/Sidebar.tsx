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
} from "lucide-react";
import clsx from "clsx";

const NAV = [
  { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
  { href: "/dashboard/simulator", label: "Phone Simulator", icon: Phone },
  { href: "/dashboard/calls", label: "Calls", icon: PhoneCall },
  { href: "/dashboard/orders", label: "Orders", icon: Package },
  { href: "/dashboard/shipments", label: "Shipments", icon: Truck },
  { href: "/dashboard/stock", label: "Stock", icon: Boxes },
  { href: "/dashboard/suppliers", label: "Suppliers", icon: Users },
  { href: "/dashboard/appointments", label: "Appointments", icon: Calendar },
  { href: "/dashboard/communications", label: "Outbound Logs", icon: MessageSquare },
  { href: "https://github.com/jeevesh2515/voxflow-voice-agent", label: "Docs", icon: FileText, external: true },
];

export default function Sidebar({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const pathname = usePathname();

  return (
    <>
      {/* Mobile overlay backdrop */}
      {isOpen && (
        <div className="fixed inset-0 z-30 bg-black/50 lg:hidden" onClick={onClose} />
      )}

      <aside
        className={clsx(
          "w-64 bg-[#111118] border-r border-[#302840]/60 flex flex-col hide-scrollbar overflow-y-auto shrink-0 select-none",
          "fixed lg:static inset-y-0 left-0 z-40 transition-transform duration-200",
          isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
        )}
      >
      <div className="flex items-center justify-between px-4 pt-4 pb-2 lg:hidden">
        <span className="text-[10px] font-label text-[#a098b0]/50 uppercase tracking-[0.2em] font-bold">
          Navigation
        </span>
        <button onClick={onClose} className="p-1 text-[#a098b0] hover:text-[#e8e0f0]">
          <X size={18} />
        </button>
      </div>

      <div className="py-2 lg:py-4 space-y-0.5">
        <div className="px-4 mb-2 hidden lg:block">
          <span className="text-[10px] font-label text-[#a098b0]/50 uppercase tracking-[0.2em] font-bold">
            Navigation
          </span>
        </div>

        {NAV.map((item) => {
          const Icon = item.icon;
          const active = !item.external && pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              target={item.external ? "_blank" : undefined}
              onClick={onClose}
              className={clsx(
                "flex items-center gap-3 px-4 py-2.5 transition-all duration-200 group text-sm font-medium",
                active
                  ? "sidebar-item-active font-bold"
                  : "text-[#a098b0] hover:text-[#ff2d78] hover:bg-[#1e1e30]/40"
              )}
            >
              <Icon size={18} className={clsx("transition-transform duration-200 group-hover:scale-110", active ? "text-[#ff2d78]" : "text-[#a098b0]")} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </div>

      {/* Bottom Status Widgets */}
      <div className="mt-auto p-4 space-y-3 border-t border-[#302840]/40">
        <div className="glass-panel p-3 rounded-lg border border-[#00ffcc]/20 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-[#a098b0] uppercase font-bold tracking-widest font-label">Queue Status</span>
            <span className="text-[10px] text-[#00ffcc] font-bold font-label">OPTIMAL</span>
          </div>
          <div className="flex gap-1">
            <div className="h-1 flex-1 bg-[#00ffcc] rounded-full shadow-[0_0_8px_#00ffcc]" />
            <div className="h-1 flex-1 bg-[#00ffcc] rounded-full shadow-[0_0_8px_#00ffcc]" />
            <div className="h-1 flex-1 bg-[#00ffcc]/30 rounded-full" />
            <div className="h-1 flex-1 bg-[#00ffcc]/30 rounded-full" />
          </div>
        </div>

        <div className="glass-panel p-3 rounded-lg border border-[#ff2d78]/20 flex items-center gap-3">
          <div className="bg-[#00ffcc]/10 p-1.5 rounded text-[#00ffcc]">
            <Zap size={14} />
          </div>
          <div>
            <p className="text-[9px] text-[#a098b0] uppercase font-bold font-label tracking-widest">System Health</p>
            <p className="text-xs font-headline font-bold text-[#00ffcc]">98.2%</p>
          </div>
        </div>
      </div>
    </aside>
    </>
  );
}
