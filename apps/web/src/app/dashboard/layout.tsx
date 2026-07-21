"use client";

import Sidebar from "@/components/Sidebar";
import { TenantProvider } from "@/lib/tenant-context";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <TenantProvider>
      <div className="min-h-screen flex bg-ink-950 text-ink-100">
        <Sidebar />
        <main className="flex-1 min-w-0 flex flex-col">{children}</main>
      </div>
    </TenantProvider>
  );
}
