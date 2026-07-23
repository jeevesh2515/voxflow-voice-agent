"use client";

import { useState } from "react";
import Sidebar from "@/components/Sidebar";
import Topbar from "@/components/Topbar";
import { TenantProvider } from "@/lib/tenant-context";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <TenantProvider>
      <div className="min-h-screen flex flex-col bg-[#0a0a12] text-[#e8e0f0] font-body selection:bg-[#ff2d78] selection:text-white overflow-hidden">
        <Topbar onToggleSidebar={() => setSidebarOpen((o) => !o)} />

        <div className="flex flex-1 h-[calc(100vh-65px)] overflow-hidden">
          <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
          <main className="flex-1 overflow-y-auto bg-[#0a0a12] p-6 lg:p-8 hide-scrollbar">
            {children}
          </main>
        </div>
      </div>
    </TenantProvider>
  );
}
