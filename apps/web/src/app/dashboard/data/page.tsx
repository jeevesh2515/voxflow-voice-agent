"use client";

import { useState } from "react";
import useSWR from "swr";
import {
  Database,
  UploadCloud,
  FileSpreadsheet,
  Download,
  Boxes,
  Users,
  ShoppingCart,
  Truck,
  Package,
  CheckCircle2,
  ShieldCheck,
  Zap,
  Layers,
} from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";
import SectionCard from "@/components/dashboard/SectionCard";
import StatCard from "@/components/dashboard/StatCard";
import CsvImportModal, { EntityType } from "@/components/dashboard/CsvImportModal";

export default function DataCenterPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const [modalOpen, setModalOpen] = useState(false);
  const [targetEntity, setTargetEntity] = useState<EntityType>("products");

  // Fetch live stats
  const { data: stock, mutate: mutateStock } = useSWR(
    ["stock", activeTenantId],
    () => api.stock({ tenant_id: activeTenantId })
  );
  const { data: suppliers, mutate: mutateSuppliers } = useSWR(
    ["suppliers", activeTenantId],
    () => api.suppliers(undefined, activeTenantId)
  );
  const { data: orders, mutate: mutateOrders } = useSWR(
    ["orders", activeTenantId],
    () => api.orders({ tenant_id: activeTenantId })
  );
  const { data: shipments, mutate: mutateShipments } = useSWR(
    ["shipments", activeTenantId],
    () => api.shipments(undefined, activeTenantId)
  );


  const totalStockUnits = stock?.reduce((acc: number, s: any) => acc + (s.quantity || 0), 0) ?? 0;

  const handleOpenImport = (entity: EntityType) => {
    setTargetEntity(entity);
    setModalOpen(true);
  };

  const handleRefreshAll = () => {
    mutateStock();
    mutateSuppliers();
    mutateOrders();
    mutateShipments();
  };

  const ENTITIES = [
    {
      id: "products" as EntityType,
      name: "Products & SKUs",
      icon: Package,
      color: "#00ffcc",
      count: stock ? Array.from(new Set(stock.map((s: any) => s.sku))).length : 0,
      countLabel: "Unique SKUs",
      description: "Master catalog containing item names, pack sizes, category hierarchies, and retail pricing.",
      requiredColumns: ["sku", "name"],
      optionalColumns: ["category", "pack_size", "mrp_inr"],
    },
    {
      id: "stock" as EntityType,
      name: "Warehouse Stock",
      icon: Boxes,
      color: "#00f0ff",
      count: totalStockUnits,
      countLabel: "Units in Stock",
      description: "Bin-level inventory levels, warehouse depot locations, and stock alerts across facilities.",
      requiredColumns: ["sku", "warehouse", "quantity"],
      optionalColumns: [],
    },
    {
      id: "suppliers" as EntityType,
      name: "Suppliers & Contacts",
      icon: Users,
      color: "#ff2d78",
      count: suppliers?.length ?? 0,
      countLabel: "Registered Contacts",
      description: "Vendor and client address book with E.164 phone numbers, GSTIN/VAT references, and PIN auth.",
      requiredColumns: ["name", "phone"],
      optionalColumns: ["id", "city", "state", "pincode", "contact_person", "auth_pin", "contact_type"],
    },
    {
      id: "orders" as EntityType,
      name: "Purchase Orders",
      icon: ShoppingCart,
      color: "#ffb800",
      count: orders?.length ?? 0,
      countLabel: "Purchase Orders",
      description: "Inbound and outbound purchase contracts, client PO references, quantities, and line item JSON.",
      requiredColumns: ["id", "supplier_id"],
      optionalColumns: ["status", "customer_po_ref", "total_qty", "notes", "items"],
    },
    {
      id: "shipments" as EntityType,
      name: "Shipments & Logistics",
      icon: Truck,
      color: "#a855f7",
      count: shipments?.length ?? 0,
      countLabel: "Active Shipments",
      description: "Carrier dispatch assignments, waybill tracking numbers, transit status, and delivery milestones.",
      requiredColumns: ["id", "order_id"],
      optionalColumns: ["status", "carrier", "tracking_no", "expected_delivery"],
    },
  ];

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Top Banner / Hero */}
      <div className="relative p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-[#140f24] via-[#1a1230] to-[#0e0a1a] border border-[#302840] overflow-hidden shadow-2xl">
        <div className="absolute right-0 top-0 w-96 h-full bg-[#00ffcc]/5 blur-[100px] pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#00ffcc]/10 border border-[#00ffcc]/30 text-[#00ffcc] text-xs font-mono">
              <Database size={13} />
              <span>Phase B: Multi-Tenant Data Ingestion</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-[#f0ecf8] tracking-tight">
              Company Data Hub & CSV Engine
            </h1>
            <p className="text-xs sm:text-sm text-[#a098b0] leading-relaxed">
              Equip your AI voice agent with full operational context. Bulk load your catalog, inventory,
              suppliers, and purchase orders via transactional CSV uploads with zero manual data entry.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => handleOpenImport("products")}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#00ffcc] hover:bg-[#00ffcc]/90 text-[#0a0a12] text-xs font-bold transition-all shadow-[0_0_25px_rgba(0,255,204,0.3)] hover:scale-102"
            >
              <UploadCloud size={16} />
              <span>Import CSV Data</span>
            </button>
          </div>
        </div>
      </div>

      {/* Metric Cards Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Catalog SKUs"
          value={stock ? String(Array.from(new Set(stock.map((s: any) => s.sku))).length) : "0"}
          subtitle={`${activeTenant.name} workspace`}
          icon={<Package size={18} className="text-[#00ffcc]" />}
        />
        <StatCard
          title="Inventory Units"
          value={totalStockUnits.toLocaleString()}
          subtitle="Across all bin locations"
          icon={<Boxes size={18} className="text-[#00f0ff]" />}
        />
        <StatCard
          title="Suppliers & Clients"
          value={String(suppliers?.length ?? 0)}
          subtitle="Verified caller contacts"
          icon={<Users size={18} className="text-[#ff2d78]" />}
        />
        <StatCard
          title="Purchase Orders"
          value={String(orders?.length ?? 0)}
          subtitle="Real-time PO lookups"
          icon={<ShoppingCart size={18} className="text-[#ffb800]" />}
        />
      </div>

      {/* Entity Ingestion Cards Grid */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-[#f0ecf8]">Supported Ingestion Entities</h2>
            <p className="text-xs text-[#a098b0]">
              Download standard format templates or import bulk files for each domain model
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {ENTITIES.map((entity) => {
            const Icon = entity.icon;
            return (
              <div
                key={entity.id}
                className="group relative p-5 rounded-2xl bg-[#0e0a1a] hover:bg-[#140f24] border border-[#302840]/80 hover:border-white/20 transition-all duration-200 shadow-lg flex flex-col justify-between space-y-4"
              >
                {/* Card Glow */}
                <div
                  className="absolute -top-12 -right-12 w-28 h-28 blur-[60px] opacity-20 pointer-events-none transition-opacity group-hover:opacity-40"
                  style={{ backgroundColor: entity.color }}
                />

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div
                      className="p-2.5 rounded-xl border border-white/10"
                      style={{ backgroundColor: `${entity.color}15`, color: entity.color }}
                    >
                      <Icon size={20} />
                    </div>
                    <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-full bg-white/5 text-[#f0ecf8] border border-white/10">
                      {entity.count} {entity.countLabel}
                    </span>
                  </div>

                  <div>
                    <h3 className="text-sm font-bold text-[#f0ecf8] group-hover:text-white transition-colors">
                      {entity.name}
                    </h3>
                    <p className="text-xs text-[#a098b0] mt-1 line-clamp-2 leading-relaxed">
                      {entity.description}
                    </p>
                  </div>

                  {/* Schema Columns Preview */}
                  <div className="space-y-1.5 pt-2 border-t border-[#302840]/40">
                    <div className="text-[10px] font-mono uppercase tracking-wider text-[#706585]">
                      Required Headers:
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {entity.requiredColumns.map((col) => (
                        <span
                          key={col}
                          className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#00ffcc]/10 text-[#00ffcc] border border-[#00ffcc]/20"
                        >
                          {col}*
                        </span>
                      ))}
                      {entity.optionalColumns.slice(0, 3).map((col) => (
                        <span
                          key={col}
                          className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-[#a098b0] border border-white/5"
                        >
                          {col}
                        </span>
                      ))}
                      {entity.optionalColumns.length > 3 && (
                        <span className="text-[10px] font-mono text-[#706585] px-1 py-0.5">
                          +{entity.optionalColumns.length - 3} more
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 pt-2">
                  <a
                    href={api.getCsvTemplateUrl(entity.id)}
                    download={`${entity.id}_template.csv`}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl bg-white/5 hover:bg-white/10 text-xs text-[#d0c8e0] font-medium border border-white/10 transition-colors"
                  >
                    <Download size={13} />
                    <span>Template</span>
                  </a>
                  <button
                    onClick={() => handleOpenImport(entity.id)}
                    className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl text-xs font-bold text-[#0a0a12] transition-transform hover:scale-102"
                    style={{ backgroundColor: entity.color }}
                  >
                    <UploadCloud size={13} />
                    <span>Import CSV</span>
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Enterprise Guarantees Feature Grid */}
      <SectionCard
        title="Enterprise Data Ingestion Safeguards"
        subtitle="How VoxFlow protects your multi-tenant database during bulk updates"
        icon={<ShieldCheck size={18} className="text-[#00ffcc]" />}
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 pt-2">
          <div className="p-4 rounded-xl bg-[#0a0712] border border-[#302840]/60 space-y-2">
            <div className="w-8 h-8 rounded-lg bg-[#00ffcc]/10 text-[#00ffcc] flex items-center justify-center font-bold">
              <Zap size={16} />
            </div>
            <h4 className="text-xs font-bold text-[#f0ecf8]">All-or-Nothing Transactional Safety</h4>
            <p className="text-xs text-[#a098b0] leading-relaxed">
              Every CSV import executes inside an atomic database transaction. If row 49 out of 50 has a
              validation flaw, zero corrupted records enter the database.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[#0a0712] border border-[#302840]/60 space-y-2">
            <div className="w-8 h-8 rounded-lg bg-[#00f0ff]/10 text-[#00f0ff] flex items-center justify-center font-bold">
              <Layers size={16} />
            </div>
            <h4 className="text-xs font-bold text-[#f0ecf8]">Idempotent Upsert Semantics</h4>
            <p className="text-xs text-[#a098b0] leading-relaxed">
              Re-uploading master inventory sheets updates existing quantities and prices without primary key
              collisions or duplicate records.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-[#0a0712] border border-[#302840]/60 space-y-2">
            <div className="w-8 h-8 rounded-lg bg-[#ff2d78]/10 text-[#ff2d78] flex items-center justify-center font-bold">
              <ShieldCheck size={16} />
            </div>
            <h4 className="text-xs font-bold text-[#f0ecf8]">Zero-Leak Tenant Isolation</h4>
            <p className="text-xs text-[#a098b0] leading-relaxed">
              Every row is bound to your tenant scope at the database layer. Imported data is instantly
              available to callers without leaking to other workspaces.
            </p>
          </div>
        </div>
      </SectionCard>

      {/* CSV Import Modal */}
      <CsvImportModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        initialEntity={targetEntity}
        onSuccess={handleRefreshAll}
      />
    </div>
  );
}
