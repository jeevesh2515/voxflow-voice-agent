"use client";

import { useState, useMemo } from "react";
import useSWR, { mutate } from "swr";
import {
  Package,
  Plus,
  Search,
  Filter,
  Download,
  Calendar,
  CheckCircle2,
  Clock,
  Truck,
  AlertCircle,
  X,
  FileText,
} from "lucide-react";
import { api } from "@/lib/api";
import { fmtRelative, statusBg, statusColor } from "@/lib/format";
import { useTenant } from "@/lib/tenant-context";
import type { Order, OrderItem } from "@/lib/types";

export default function OrdersPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: orders, error, isLoading } = useSWR(
    ["orders", activeTenantId],
    () => api.orders({ tenant_id: activeTenantId }),
  );
  const { data: suppliers } = useSWR(
    ["suppliers", activeTenantId],
    () => api.suppliers(undefined, activeTenantId),
  );
  const { data: stock } = useSWR(
    ["stock", activeTenantId],
    () => api.stock({ tenant_id: activeTenantId }),
  );

  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  // Form state for creating an order
  const [newSupplierId, setNewSupplierId] = useState("");
  const [newSku, setNewSku] = useState("");
  const [newQty, setNewQty] = useState(50);
  const [newNotes, setNewNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  const filteredOrders = useMemo(() => {
    if (!orders) return [];
    return (orders as Order[]).filter((o) => {
      const matchSearch =
        o.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        o.supplier_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (o.notes && o.notes.toLowerCase().includes(searchQuery.toLowerCase()));
      const matchStatus = statusFilter === "all" || o.status === statusFilter;
      return matchSearch && matchStatus;
    });
  }, [orders, searchQuery, statusFilter]);

  const stats = useMemo(() => {
    const list = (orders as Order[]) || [];
    return {
      total: list.length,
      pending: list.filter((o) => o.status === "pending").length,
      confirmed: list.filter((o) => o.status === "confirmed").length,
      shipped: list.filter((o) => o.status === "shipped" || o.status === "delivered").length,
      totalUnits: list.reduce((sum, o) => sum + (o.total_qty || 0), 0),
    };
  }, [orders]);

  const handleCreateOrder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSupplierId) {
      setFormError("Please select a verified supplier");
      return;
    }
    if (!newSku) {
      setFormError("Please select a product SKU");
      return;
    }
    setFormError("");
    setIsSubmitting(true);

    try {
      await api.createOrder(
        {
          supplier_id: newSupplierId,
          items: [{ sku: newSku, quantity: Number(newQty) || 1 }],
          notes: newNotes.trim(),
        },
        activeTenantId,
      );
      mutate(["orders", activeTenantId]);
      mutate(["summary", activeTenantId]);
      setIsCreateOpen(false);
      setNewNotes("");
    } catch (err: any) {
      setFormError(err.message || "Failed to create order");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleExportCSV = () => {
    if (!orders || orders.length === 0) return;
    const headers = "Order ID,Supplier ID,Status,Total Quantity,Created At\n";
    const rows = (orders as Order[])
      .map((o) => `"${o.id}","${o.supplier_id}","${o.status}",${o.total_qty},"${o.created_at}"`)
      .join("\n");
    const blob = new Blob([headers + rows], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `orders_${activeTenantId}_${Date.now()}.csv`;
    link.click();
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* ==================== PAGE HEADER ==================== */}
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-label uppercase tracking-widest text-[#a098b0] mb-1">
            <span>Operations</span>
            <span>/</span>
            <span className="text-[#00ffcc] font-bold">{activeTenant.name}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-headline font-extrabold text-[#e8e0f0] tracking-[0.05em] uppercase">
            Purchase <span className="text-[#ff2d78] text-glow-primary">Orders</span>
          </h1>
          <p className="text-[#a098b0] font-body text-sm mt-1">
            Automated voice & ERP purchase order ledger with real-time supplier acknowledgement.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleExportCSV}
            className="bg-[#1e1e30] border border-[#302840] px-4 py-2 rounded-xl text-xs font-label font-bold uppercase tracking-widest flex items-center gap-2 hover:border-[#00ffcc] text-[#e8e0f0] transition-all"
          >
            <Download size={14} className="text-[#00ffcc]" /> Export CSV
          </button>
          <button
            onClick={() => {
              if (suppliers && suppliers.length > 0) setNewSupplierId(suppliers[0].id);
              if (stock && stock.length > 0) setNewSku(stock[0].sku);
              setIsCreateOpen(true);
            }}
            className="bg-[#ff2d78] text-[#1a0010] px-4 py-2 rounded-xl text-xs font-label font-bold uppercase tracking-widest flex items-center gap-2 neon-glow-primary hover:scale-105 active:scale-95 transition-all"
          >
            <Plus size={15} /> Create Order
          </button>
        </div>
      </header>

      {/* ==================== STAT CARDS ==================== */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-4 rounded-2xl border border-[#ff2d78]/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>Total Orders</span>
            <Package size={16} className="text-[#ff2d78]" />
          </div>
          <div className="text-2xl font-headline font-bold text-[#e8e0f0]">{stats.total}</div>
          <div className="text-[10px] text-[#a098b0] mt-1">{stats.totalUnits.toLocaleString()} units total</div>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-[#ffe04a]/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>Pending Review</span>
            <Clock size={16} className="text-[#ffe04a]" />
          </div>
          <div className="text-2xl font-headline font-bold text-[#ffe04a]">{stats.pending}</div>
          <div className="text-[10px] text-[#a098b0] mt-1">Awaiting 2FA signature</div>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-[#00ffcc]/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>Confirmed</span>
            <CheckCircle2 size={16} className="text-[#00ffcc]" />
          </div>
          <div className="text-2xl font-headline font-bold text-[#00ffcc]">{stats.confirmed}</div>
          <div className="text-[10px] text-[#a098b0] mt-1">Supplier verified</div>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-blue-500/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>Fulfilled / Shipped</span>
            <Truck size={16} className="text-blue-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-blue-400">{stats.shipped}</div>
          <div className="text-[10px] text-[#a098b0] mt-1">Dispatched to carrier</div>
        </div>
      </div>

      {/* ==================== FILTERS & SEARCH ==================== */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between bg-[#111118]/80 p-3 rounded-2xl border border-[#302840]/60">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#a098b0]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search PO number, supplier, items..."
            className="w-full bg-[#181824] border border-[#302840]/60 rounded-xl pl-9 pr-4 py-2 text-xs text-[#e8e0f0] placeholder:text-[#a098b0]/50 focus:outline-none focus:border-[#ff2d78] transition-all font-body"
          />
        </div>
        <div className="flex items-center gap-2 overflow-x-auto">
          {["all", "pending", "confirmed", "shipped", "delivered"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-xl text-xs font-label uppercase tracking-wider transition-all shrink-0 ${
                statusFilter === st
                  ? "bg-[#ff2d78] text-[#1a0010] font-bold shadow-[0_0_12px_rgba(255,45,120,0.4)]"
                  : "bg-[#181824] text-[#a098b0] hover:text-[#e8e0f0] border border-[#302840]/60"
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* ==================== ORDERS TABLE ==================== */}
      <div className="glass-panel rounded-2xl border border-[#302840]/60 overflow-hidden shadow-2xl">
        {isLoading && (
          <div className="py-16 text-center text-[#a098b0] text-xs font-label uppercase tracking-widest flex items-center justify-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#ff2d78] animate-ping" /> Loading orders ledger...
          </div>
        )}

        {error && (
          <div className="p-6 text-center text-[#ff2d78] bg-[#ff2d78]/5 text-xs font-body">
            Failed to load orders. Please verify backend API connectivity.
          </div>
        )}

        {!isLoading && !error && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm font-body">
              <thead className="bg-[#181824]/90 border-b border-[#302840]/60 text-[10px] font-label uppercase tracking-wider text-[#a098b0]">
                <tr>
                  <th className="px-5 py-3.5">Order ID</th>
                  <th className="px-5 py-3.5">Supplier</th>
                  <th className="px-5 py-3.5">Items & SKUs</th>
                  <th className="px-5 py-3.5 text-right">Total Units</th>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5 text-right">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#302840]/40">
                {filteredOrders.map((o) => (
                  <tr
                    key={o.id}
                    onClick={() => setSelectedOrder(o)}
                    className="hover:bg-[#1e1e30]/50 cursor-pointer transition-colors group"
                  >
                    <td className="px-5 py-4 font-headline font-bold text-[#ff2d78] group-hover:text-glow-primary text-xs">
                      {o.id}
                    </td>
                    <td className="px-5 py-4 text-[#e8e0f0] font-medium text-xs">
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded-lg bg-[#00ffcc]/10 border border-[#00ffcc]/30 flex items-center justify-center text-[#00ffcc] text-[10px] font-bold">
                          {o.supplier_id.slice(-3).toUpperCase()}
                        </span>
                        {o.supplier_id}
                      </div>
                    </td>
                    <td className="px-5 py-4 text-[#a098b0] text-xs font-mono">
                      {(o.items as OrderItem[])?.map((i) => `${i.sku} × ${i.quantity}`).join(", ") || "—"}
                    </td>
                    <td className="px-5 py-4 text-right font-headline font-bold text-[#e8e0f0] text-xs">
                      {o.total_qty.toLocaleString()}
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={`text-[10px] font-label font-bold uppercase px-2.5 py-1 rounded-full border ${
                          o.status === "confirmed"
                            ? "bg-[#00ffcc]/10 text-[#00ffcc] border-[#00ffcc]/30"
                            : o.status === "pending"
                            ? "bg-[#ffe04a]/10 text-[#ffe04a] border-[#ffe04a]/30"
                            : "bg-[#ff2d78]/10 text-[#ff2d78] border-[#ff2d78]/30"
                        }`}
                      >
                        {o.status}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-right text-[11px] font-mono text-[#a098b0]">
                      {fmtRelative(o.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filteredOrders.length === 0 && (
              <div className="p-16 text-center space-y-3">
                <Package className="mx-auto text-[#5a5068]" size={36} />
                <div className="text-sm text-[#e8e0f0] font-headline font-semibold">No purchase orders found</div>
                <p className="text-xs text-[#a098b0] max-w-sm mx-auto">
                  {searchQuery
                    ? `No orders matching "${searchQuery}". Try clearing search filters.`
                    : `Create your first purchase order or test the AI Voice Agent to generate orders automatically.`}
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ==================== CREATE ORDER MODAL ==================== */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-[#111118] border border-[#ff2d78]/40 rounded-2xl p-6 sm:p-8 max-w-md w-full shadow-[0_0_50px_rgba(255,45,120,0.2)] space-y-5 relative">
            <button
              onClick={() => setIsCreateOpen(false)}
              className="absolute top-5 right-5 text-[#a098b0] hover:text-[#e8e0f0] transition-colors"
            >
              <X size={18} />
            </button>

            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#ff2d78]/15 border border-[#ff2d78]/40 flex items-center justify-center text-[#ff2d78]">
                <Package size={20} />
              </div>
              <div>
                <h3 className="font-headline font-bold text-lg text-[#e8e0f0]">Create Purchase Order</h3>
                <p className="text-xs text-[#a098b0] font-body">Manual PO dispatch for {activeTenant.name}</p>
              </div>
            </div>

            <form onSubmit={handleCreateOrder} className="space-y-4">
              <div>
                <label className="text-[10px] font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                  Verified Supplier
                </label>
                <select
                  value={newSupplierId}
                  onChange={(e) => setNewSupplierId(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#181824] border border-[#302840] text-xs text-[#e8e0f0] focus:border-[#ff2d78] focus:outline-none"
                  required
                >
                  <option value="">Select Supplier...</option>
                  {(suppliers || []).map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.id}) — {s.city}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                    Product SKU
                  </label>
                  <select
                    value={newSku}
                    onChange={(e) => setNewSku(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#181824] border border-[#302840] text-xs text-[#e8e0f0] focus:border-[#ff2d78] focus:outline-none"
                    required
                  >
                    <option value="">Select SKU...</option>
                    {(stock || []).map((st) => (
                      <option key={`${st.warehouse}-${st.sku}`} value={st.sku}>
                        {st.sku} ({st.name})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[10px] font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                    Order Quantity
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={newQty}
                    onChange={(e) => setNewQty(Math.max(1, parseInt(e.target.value) || 1))}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-[#181824] border border-[#302840] text-xs text-[#e8e0f0] focus:border-[#ff2d78] focus:outline-none"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="text-[10px] font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                  Order Notes / Shipping Instructions
                </label>
                <textarea
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  placeholder="e.g. Expedited warehouse dispatch requested"
                  rows={2}
                  className="w-full px-3.5 py-2 rounded-xl bg-[#181824] border border-[#302840] text-xs text-[#e8e0f0] focus:border-[#ff2d78] focus:outline-none"
                />
              </div>

              {formError && (
                <div className="text-xs text-[#ff2d78] bg-[#ff2d78]/10 border border-[#ff2d78]/30 rounded-xl p-2.5">
                  {formError}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-4 py-2.5 rounded-xl text-xs font-label uppercase font-bold text-[#a098b0] hover:text-[#e8e0f0] bg-[#181824]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2.5 rounded-xl bg-[#ff2d78] text-[#1a0010] text-xs font-headline font-bold uppercase tracking-wider neon-glow-primary hover:scale-105 active:scale-95 disabled:opacity-50"
                >
                  {isSubmitting ? "Submitting..." : "Confirm & Dispatch PO"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ==================== ORDER DETAIL DRAWER ==================== */}
      {selectedOrder && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-[#111118] border border-[#00ffcc]/40 rounded-2xl p-6 sm:p-8 max-w-lg w-full shadow-[0_0_50px_rgba(0,255,204,0.15)] space-y-6 relative">
            <button
              onClick={() => setSelectedOrder(null)}
              className="absolute top-5 right-5 text-[#a098b0] hover:text-[#e8e0f0] transition-colors"
            >
              <X size={18} />
            </button>

            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#00ffcc]/15 border border-[#00ffcc]/40 flex items-center justify-center text-[#00ffcc]">
                <FileText size={20} />
              </div>
              <div>
                <h3 className="font-headline font-bold text-lg text-[#e8e0f0]">Order Details</h3>
                <span className="font-mono text-xs text-[#00ffcc]">{selectedOrder.id}</span>
              </div>
            </div>

            <div className="space-y-3 text-xs bg-[#181824] p-4 rounded-xl border border-[#302840]/60">
              <div className="flex justify-between">
                <span className="text-[#a098b0] uppercase font-label">Supplier ID:</span>
                <span className="text-[#e8e0f0] font-bold">{selectedOrder.supplier_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#a098b0] uppercase font-label">Status:</span>
                <span className="text-[#00ffcc] font-bold uppercase">{selectedOrder.status}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#a098b0] uppercase font-label">Total Quantity:</span>
                <span className="text-[#e8e0f0] font-bold">{selectedOrder.total_qty} units</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#a098b0] uppercase font-label">Created:</span>
                <span className="text-[#a098b0] font-mono">{new Date(selectedOrder.created_at).toLocaleString("en-IN")}</span>
              </div>
              {selectedOrder.notes && (
                <div className="pt-2 border-t border-[#302840]/60">
                  <span className="text-[#a098b0] uppercase font-label block mb-1">Notes:</span>
                  <p className="text-[#e8e0f0]">{selectedOrder.notes}</p>
                </div>
              )}
            </div>

            <div>
              <h4 className="text-xs font-label uppercase tracking-widest text-[#a098b0] mb-2">Item Breakdown</h4>
              <div className="space-y-1.5">
                {(selectedOrder.items as OrderItem[])?.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex justify-between items-center p-3 rounded-xl bg-[#181824] border border-[#302840]/40 text-xs font-mono"
                  >
                    <span className="text-[#00ffcc]">{item.sku}</span>
                    <span className="text-[#e8e0f0] font-bold">{item.quantity} units</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setSelectedOrder(null)}
                className="px-5 py-2 rounded-xl bg-[#1e1e30] text-[#e8e0f0] text-xs font-label uppercase tracking-wider hover:bg-[#28283e]"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
