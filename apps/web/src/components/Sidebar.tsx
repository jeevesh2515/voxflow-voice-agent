"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Phone, PhoneCall, Package, Truck, Boxes, Users, Calendar, MessageSquare, BookOpen,
} from "lucide-react";
import clsx from "clsx";

const NAV = [
  { href: "/dashboard",             label: "Overview",       icon: LayoutDashboard },
  { href: "/dashboard/simulator",   label: "Phone Simulator", icon: Phone },
  { href: "/dashboard/calls",       label: "Calls",          icon: PhoneCall },
  { href: "/dashboard/orders",      label: "Orders",         icon: Package },
  { href: "/dashboard/shipments",   label: "Shipments",      icon: Truck },
  { href: "/dashboard/stock",       label: "Stock",          icon: Boxes },
  { href: "/dashboard/suppliers",   label: "Suppliers",      icon: Users },
  { href: "/dashboard/appointments",label: "Appointments",   icon: Calendar },
  { href: "/dashboard/communications", label: "Outbound Logs", icon: MessageSquare },
  { href: "https://github.com/jeevesh2515/voxflow-voice-agent", label: "Docs", icon: BookOpen, external: true },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 shrink-0 border-r border-ink-700/60 bg-ink-900/60 flex flex-col">
      <div className="px-5 py-5 border-b border-ink-700/60">
        <Link href="/dashboard" className="flex items-center gap-2 group">
          <div className="h-8 w-8 rounded-md bg-gradient-to-br from-vox-500 to-vox-700 grid place-items-center font-bold text-white text-sm">
            V
          </div>
          <div>
            <div className="text-sm font-semibold tracking-tight text-ink-50">VoxFlow</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-ink-400">Voice Agent</div>
          </div>
        </Link>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {NAV.map((item) => {
          const Icon = item.icon;
          const active = !item.external && pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              target={item.external ? "_blank" : undefined}
              className={clsx(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                active
                  ? "bg-vox-500/15 text-vox-300 border border-vox-500/30 font-medium"
                  : "text-ink-300 hover:bg-ink-800/60 hover:text-ink-50 border border-transparent",
              )}
            >
              <Icon size={16} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="px-4 py-3 border-t border-ink-700/60 text-[10px] font-mono text-ink-500 uppercase tracking-wider">
        v0.1.0 · multi-tenant
      </div>
    </aside>
  );
}
