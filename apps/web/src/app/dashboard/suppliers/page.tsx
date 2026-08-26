"use client";

import { useState, useMemo } from "react";
import useSWR from "swr";
import { Users, Search, UploadCloud } from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";
import SectionCard from "@/components/dashboard/SectionCard";
import DataTable from "@/components/dashboard/DataTable";
import CsvImportModal from "@/components/dashboard/CsvImportModal";

export default function SuppliersPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: suppliers, error, isLoading, mutate } = useSWR(["suppliers", activeTenantId], () =>
    api.suppliers(undefined, activeTenantId),
  );

  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);

  const filteredSuppliers = useMemo(() => {
    if (!suppliers) return [];
    if (!search.trim()) return suppliers;
    const q = search.toLowerCase();
    return suppliers.filter((s) =>
      s.name.toLowerCase().includes(q) ||
      s.contact_person.toLowerCase().includes(q) ||
      s.city.toLowerCase().includes(q) ||
      s.phone.includes(q)
    );
  }, [suppliers, search]);

  const columns = [
    {
      key: "id",
      label: "ID",
      render: (s: any) => <span className="font-mono text-[#ff2d78] text-xs">{s.id}</span>,
    },
    {
      key: "name",
      label: "Name",
      render: (s: any) => <span className="text-[#e8e0f0] font-medium">{s.name}</span>,
    },
    {
      key: "contact",
      label: "Contact",
      render: (s: any) => <span className="text-[#a098b0] text-xs">{s.contact_person}</span>,
    },
    {
      key: "phone",
      label: "Phone",
      render: (s: any) => <span className="font-mono text-[#a098b0] text-xs">{s.phone}</span>,
    },
    {
      key: "city",
      label: "City",
      render: (s: any) => <span className="text-[#a098b0] text-xs">{s.city}</span>,
    },
    {
      key: "state",
      label: "State",
      render: (s: any) => <span className="text-[#a098b0] text-xs">{s.state}</span>,
    },
    {
      key: "gstin",
      label: "GSTIN",
      render: (s: any) => <span className="font-mono text-[#5a5068] text-[10px]">{s.gstin}</span>,
    },
  ];

  return (
    <div className="space-y-6">
      <SectionCard
        title="Suppliers Directory"
        subtitle={`${activeTenant.name} · ${suppliers?.length ?? 0} total`}
        icon={<Users size={18} className="text-[#ffe04a]" />}
        action={
          <div className="flex items-center gap-2">
            <button
              onClick={() => setModalOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#ffe04a]/10 hover:bg-[#ffe04a]/20 border border-[#ffe04a]/30 text-[#ffe04a] text-xs font-bold transition-colors"
            >
              <UploadCloud size={13} />
              <span>Import CSV</span>
            </button>
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#a098b0]" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search suppliers..."
                className="pl-9 pr-4 py-2 rounded-lg bg-[#0a0a12] border border-[#302840] text-xs text-[#e8e0f0] placeholder-[#5a5068] focus:outline-none focus:border-[#ffe04a]/50 w-48"
              />
            </div>
          </div>
        }
      >
        {isLoading && <div className="text-center text-[#a098b0] py-12 text-sm">Loading suppliers...</div>}
        {error && <div className="rounded border border-danger-500/30 bg-danger-500/10 p-3 text-sm text-danger-500">Failed to load suppliers. Is the API running?</div>}
        {!isLoading && !error && (
          <DataTable
            columns={columns}
            data={filteredSuppliers}
            keyExtractor={(s) => s.id}
            loading={isLoading}
            emptyState={
              <div className="px-4 py-12 text-center space-y-3">
                <Users size={32} className="mx-auto text-[#5a5068]" />
                <div className="text-sm text-[#a098b0]">No registered suppliers for {activeTenant.name}.</div>
                <button
                  onClick={() => setModalOpen(true)}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#ffe04a] text-[#0a0a12] text-xs font-bold shadow-lg"
                >
                  <UploadCloud size={14} />
                  <span>Import Suppliers via CSV</span>
                </button>
              </div>
            }
          />
        )}
      </SectionCard>

      <CsvImportModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        initialEntity="suppliers"
        onSuccess={() => mutate()}
      />
    </div>
  );
}

