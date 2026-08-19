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
  BarChart3,
  Sliders,
  FileText,
  Zap,
  X,
  AlertTriangle,
  Radio,
} from "lucide-react";
import clsx from "clsx";

interface NavItem {
  href: string;
  label: string;
  icon: any;
  badge?: string;
  external?: boolean;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: "Core Operations",
    items: [
      { href: "/dashboard", label: "Overview", icon: LayoutDashboard },
      { href: "/dashboard/simulator", label: "Voice Simulator", icon: Phone, badge: "Live" },
      { href: "/dashboard/calls", label: "Call Records & Audio", icon: PhoneCall },
      { href: "/dashboard/escalations", label: "Escalations Queue", icon: AlertTriangle },
    ],
  },
  {
    title: "Supply Chain & Logistics",
    items: [
      { href: "/dashboard/orders", label: "Purchase Orders", icon: Package },
      { href: "/dashboard/shipments", label: "Shipments Tracking", icon: Truck },
      { href: "/dashboard/stock", label: "Stock & Inventory", icon: Boxes },
      { href: "/dashboard/suppliers", label: "Suppliers Directory", icon: Users },
      { href: "/dashboard/appointments", label: "Dock Appointments", icon: Calendar },
    ],
  },
  {
    title: "Intelligence & Platform",
    items: [
      { href: "/dashboard/communications", label: "Email & Outbound Logs", icon: MessageSquare },
      { href: "/dashboard/analytics", label: "Analytics & Evals", icon: BarChart3 },
      { href: "/dashboard/settings", label: "Voice Agent & SaaS", icon: Sliders },
      { href: "https://github.com/jeevesh2515/voxflow-voice-agent", label: "GitHub & Docs", icon: FileText, external: true },
    ],
  },
];

export default function Sidebar({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const pathname = usePathname();

  return (
    <>
      {/* Mobile overlay backdrop */}
      {isOpen && (
        <div className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm lg:hidden" onClick={onClose} />
      )}

      <aside
        className={clsx(
          "w-64 bg-[#0d0d16] border-r border-[#242436] flex flex-col hide-scrollbar overflow-y-auto shrink-0 select-none",
          "fixed lg:static inset-y-0 left-0 z-40 transition-transform duration-200",
          isOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full lg:translate-x-0",
        )}
      >
        <div className="flex items-center justify-between px-5 pt-5 pb-2 lg:hidden">
          <span className="text-xs font-headline font-bold text-[#f1f5f9] tracking-wider uppercase">
            Operations Menu
          </span>
          <button onClick={onClose} className="p-1.5 rounded-lg text-[#94a3b8] hover:text-[#ffffff] hover:bg-[#1e1e30]">
            <X size={18} />
          </button>
        </div>

        <div className="py-4 space-y-6 flex-1 px-3">
          {NAV_SECTIONS.map((section, idx) => (
            <div key={section.title} className="space-y-1">
              <div className="px-3 pb-1">
                <span className="text-[10px] font-label text-[#94a3b8]/70 uppercase tracking-[0.18em] font-bold">
                  {section.title}
                </span>
              </div>

              {section.items.map((item) => {
                const Icon = item.icon;
                const active = !item.external && (pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href)));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    target={item.external ? "_blank" : undefined}
                    onClick={onClose}
                    className={clsx(
                      "flex items-center justify-between px-3.5 py-2 rounded-xl transition-all duration-150 group text-xs font-medium",
                      active
                        ? "bg-[#ff2d78]/15 text-[#ffffff] font-semibold border border-[#ff2d78]/30 shadow-sm"
                        : "text-[#cbd5e1] hover:text-[#ffffff] hover:bg-[#181826]",
                    )}
                  >
                    <div className="flex items-center gap-3">
                      <Icon
                        size={17}
                        className={clsx(
                          "transition-transform duration-150 group-hover:scale-105 shrink-0",
                          active ? "text-[#ff2d78]" : "text-[#94a3b8] group-hover:text-[#ff2d78]",
                        )}
                      />
                      <span className="truncate">{item.label}</span>
                    </div>
                    {item.badge && (
                      <span className="px-1.5 py-0.5 rounded text-[9px] font-mono font-bold bg-[#00ffcc]/15 text-[#00ffcc] border border-[#00ffcc]/30">
                        {item.badge}
                      </span>
                    )}
                  </Link>
                );
              })}
            </div>
          ))}
        </div>

        {/* Bottom Telephony & Engine Status */}
        <div className="p-3.5 border-t border-[#242436] space-y-2.5 bg-[#0a0a10]">
          <div className="p-2.5 rounded-xl bg-[#141420] border border-[#2c2c40] flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="relative">
                <Radio size={15} className="text-[#00ffcc]" />
                <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-[#00ffcc] animate-ping" />
              </div>
              <div className="flex flex-col">
                <span className="text-[10px] font-label uppercase tracking-widest text-[#94a3b8] font-bold">
                  Groq STT & LLM
                </span>
                <span className="text-xs font-headline font-bold text-[#f1f5f9]">Sub-350ms Live</span>
              </div>
            </div>
            <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 bg-[#00ffcc]/10 text-[#00ffcc] rounded border border-[#00ffcc]/30">
              OK
            </span>
          </div>

          <div className="px-1 flex items-center justify-between text-[10px] text-[#64748b] font-mono">
            <span>v0.1.0 • Multi-Tenant</span>
            <span className="text-[#94a3b8]">Render Cloud</span>
          </div>
        </div>
      </aside>
    </>
  );
}
