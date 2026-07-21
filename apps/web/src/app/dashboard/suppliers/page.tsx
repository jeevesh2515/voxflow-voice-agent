"use client";

import useSWR from "swr";
import Topbar from "@/components/Topbar";
import { api } from "@/lib/api";
import { Users } from "lucide-react";
import { useTenant } from "@/lib/tenant-context";

export default function SuppliersPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: suppliers } = useSWR(["suppliers", activeTenantId], () =>
    api.suppliers(undefined, activeTenantId),
  );

  return (
    <>
      <Topbar title="Suppliers Directory" subtitle={`${activeTenant.name} · ${suppliers?.length ?? 0} total`} />
      <div className="p-6">
        <div className="rounded-lg border border-ink-700/60 bg-ink-900/40 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-ink-900/60 text-[10px] font-mono uppercase tracking-wider text-ink-400">
              <tr>
                <th className="text-left px-4 py-3">ID</th>
                <th className="text-left px-4 py-3">Name</th>
                <th className="text-left px-4 py-3">Contact</th>
                <th className="text-left px-4 py-3">Phone</th>
                <th className="text-left px-4 py-3">City</th>
                <th className="text-left px-4 py-3">State</th>
                <th className="text-left px-4 py-3">GSTIN</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-800/60">
              {suppliers?.map((s) => (
                <tr key={s.id} className="hover:bg-ink-800/30">
                  <td className="px-4 py-3 font-mono text-vox-300 text-xs">{s.id}</td>
                  <td className="px-4 py-3 text-ink-100">{s.name}</td>
                  <td className="px-4 py-3 text-ink-300">{s.contact_person}</td>
                  <td className="px-4 py-3 font-mono text-ink-300 text-xs">{s.phone}</td>
                  <td className="px-4 py-3 text-ink-300">{s.city}</td>
                  <td className="px-4 py-3 text-ink-300">{s.state}</td>
                  <td className="px-4 py-3 font-mono text-ink-500 text-xs">{s.gstin}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {(!suppliers || suppliers.length === 0) && (
            <div className="px-4 py-12 text-center">
              <Users className="mx-auto mb-3 text-ink-600" />
              <div className="text-sm text-ink-300">No registered suppliers for {activeTenant.name}.</div>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
