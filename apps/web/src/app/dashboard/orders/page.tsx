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
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#12121e] p-6 rounded-2xl border border-[#242436] shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-mono text-[#94a3b8]">
            <span>Operations</span>
            <span>/</span>
            <span className="text-[#00ffcc] font-bold">{activeTenant.name}</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-headline font-bold text-white tracking-tight">
            Purchase Orders Ledger
          </h1>
          <p className="text-xs sm:text-sm text-[#94a3b8]">
            Automated voice & ERP purchase order ledger with real-time supplier acknowledgement.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleExportCSV}
            className="bg-[#181826] hover:bg-[#202034] border border-[#2c2c40] px-4 py-2 rounded-xl text-xs font-medium flex items-center gap-2 text-[#cbd5e1] hover:text-white transition-colors"
          >
            <Download size={14} className="text-[#00ffcc]" />
            <span>Export CSV</span>
          </button>
          <button
            onClick={() => {
              if (suppliers && suppliers.length > 0) setNewSupplierId(suppliers[0].id);
              if (stock && stock.length > 0) setNewSku(stock[0].sku);
              setIsCreateOpen(true);
            }}
            className="bg-[#ff2d78] hover:bg-[#e02669] text-white px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 shadow-sm transition-colors"
          >
            <Plus size={15} />
            <span>Create Order</span>
          </button>
        </div>
      </header>

      {/* ==================== STAT CARDS ==================== */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Total Orders</span>
            <Package size={16} className="text-[#ff2d78]" />
          </div>
          <div className="text-2xl font-headline font-bold text-white">{stats.total}</div>
          <div className="text-xs text-[#94a3b8] mt-1">{stats.totalUnits.toLocaleString()} units total</div>
        </div>

        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Pending Review</span>
            <Clock size={16} className="text-amber-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-amber-400">{stats.pending}</div>
          <div className="text-xs text-[#94a3b8] mt-1">Awaiting confirmation</div>
        </div>

        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Confirmed</span>
            <CheckCircle2 size={16} className="text-[#00ffcc]" />
          </div>
          <div className="text-2xl font-headline font-bold text-[#00ffcc]">{stats.confirmed}</div>
          <div className="text-xs text-[#94a3b8] mt-1">Supplier verified</div>
        </div>

        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Fulfilled / Shipped</span>
            <Truck size={16} className="text-blue-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-blue-400">{stats.shipped}</div>
          <div className="text-xs text-[#94a3b8] mt-1">Dispatched to logistics</div>
        </div>
      </div>

      {/* ==================== FILTERS & SEARCH ==================== */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between bg-[#141422] p-3 rounded-2xl border border-[#28283c]">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#64748b]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search PO number, supplier, items..."
            className="w-full bg-[#10101a] border border-[#28283c] rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder:text-[#64748b] focus:outline-none focus:border-[#ff2d78]"
          />
        </div>
        <div className="flex items-center bg-[#10101a] p-1 rounded-xl border border-[#28283c] overflow-x-auto">
          {["all", "pending", "confirmed", "shipped", "delivered"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors ${
                statusFilter === st
                  ? "bg-[#ff2d78] text-white"
                  : "text-[#94a3b8] hover:text-white"
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* ==================== ORDERS TABLE ==================== */}
      <div className="bg-[#141422] rounded-2xl border border-[#28283c] overflow-hidden shadow-sm">
        {isLoading && (
          <div className="py-16 text-center text-[#94a3b8] text-xs">
            Loading orders ledger...
          </div>
        )}

        {error && (
          <div className="p-6 text-center text-red-400 bg-red-500/10 text-xs">
            Failed to load orders. Please verify backend API connectivity.
          </div>
        )}

        {!isLoading && !error && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#181828] border-b border-[#28283c] text-[11px] font-mono uppercase tracking-wider text-[#94a3b8]">
                <tr>
                  <th className="px-5 py-3.5">Order ID</th>
                  <th className="px-5 py-3.5">Supplier</th>
                  <th className="px-5 py-3.5">Items & SKUs</th>
                  <th className="px-5 py-3.5 text-right">Total Units</th>
                  <th className="px-5 py-3.5">Status</th>
                  <th className="px-5 py-3.5 text-right">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#242436]">
                {filteredOrders.map((o) => (
                  <tr
                    key={o.id}
                    onClick={() => setSelectedOrder(o)}
                    className="hover:bg-[#181828] cursor-pointer transition-colors"
                  >
                    <td className="px-5 py-4 font-mono font-bold text-[#ff2d78]">
                      {o.id}
                    </td>
                    <td className="px-5 py-4 text-white font-medium">
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded-lg bg-[#00ffcc]/15 border border-[#00ffcc]/30 flex items-center justify-center text-[#00ffcc] text-[10px] font-bold">
                          {o.supplier_id.slice(-3).toUpperCase()}
                        </span>
                        {o.supplier_id}
                      </div>
                    </td>
                    <td className="px-5 py-4 text-[#94a3b8] font-mono">
                      {(o.items as OrderItem[])?.map((i) => `${i.sku} × ${i.quantity}`).join(", ") || "—"}
                    </td>
                    <td className="px-5 py-4 text-right font-bold text-white">
                      {o.total_qty.toLocaleString()}
                    </td>
                    <td className="px-5 py-4">
                      <span
                        className={`text-[10px] font-mono font-bold uppercase px-2.5 py-1 rounded-md border ${
                          o.status === "confirmed"
                            ? "bg-[#00ffcc]/15 text-[#00ffcc] border-[#00ffcc]/30"
                            : o.status === "pending"
                            ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
                            : "bg-[#ff2d78]/15 text-[#ff2d78] border-[#ff2d78]/30"
                        }`}
                      >
                        {o.status}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-right font-mono text-[#94a3b8]">
                      {fmtRelative(o.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {filteredOrders.length === 0 && (
              <div className="p-16 text-center space-y-3">
                <Package className="mx-auto text-[#64748b]" size={36} />
                <div className="text-sm text-white font-headline font-semibold">No purchase orders found</div>
                <p className="text-xs text-[#94a3b8] max-w-sm mx-auto">
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
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#141422] border border-[#28283c] rounded-2xl p-6 sm:p-8 max-w-md w-full shadow-2xl space-y-5 relative">
            <button
              onClick={() => setIsCreateOpen(false)}
              className="absolute top-5 right-5 text-[#94a3b8] hover:text-white transition-colors"
            >
              <X size={18} />
            </button>

            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#ff2d78]/15 border border-[#ff2d78]/30 flex items-center justify-center text-[#ff2d78]">
                <Package size={20} />
              </div>
              <div>
                <h3 className="font-headline font-bold text-base text-white">Create Purchase Order</h3>
                <p className="text-xs text-[#94a3b8]">Manual PO dispatch for {activeTenant.name}</p>
              </div>
            </div>

            <form onSubmit={handleCreateOrder} className="space-y-4">
              <div>
                <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
                  Verified Supplier
                </label>
                <select
                  value={newSupplierId}
                  onChange={(e) => setNewSupplierId(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#ff2d78] focus:outline-none"
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
                  <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
                    Product SKU
                  </label>
                  <select
                    value={newSku}
                    onChange={(e) => setNewSku(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#ff2d78] focus:outline-none"
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
                  <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
                    Order Quantity
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={newQty}
                    onChange={(e) => setNewQty(Math.max(1, parseInt(e.target.value) || 1))}
                    className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#ff2d78] focus:outline-none"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
                  Order Notes / Shipping Instructions
                </label>
                <textarea
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  placeholder="e.g. Expedited warehouse dispatch requested"
                  rows={2}
                  className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#ff2d78] focus:outline-none"
                />
              </div>

              {formError && (
                <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-xl p-2.5">
                  {formError}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-[#94a3b8] hover:text-white bg-[#181826] border border-[#28283c]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-xl bg-[#ff2d78] hover:bg-[#e02669] text-white text-xs font-bold transition-colors disabled:opacity-50"
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
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#141422] border border-[#28283c] rounded-2xl p-6 sm:p-8 max-w-lg w-full shadow-2xl space-y-6 relative">
            <button
              onClick={() => setSelectedOrder(null)}
              className="absolute top-5 right-5 text-[#94a3b8] hover:text-white transition-colors"
            >
              <X size={18} />
            </button>

            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#00ffcc]/15 border border-[#00ffcc]/30 flex items-center justify-center text-[#00ffcc]">
                <FileText size={20} />
              </div>
              <div>
                <h3 className="font-headline font-bold text-base text-white">Order Details</h3>
                <span className="font-mono text-xs text-[#00ffcc]">#{selectedOrder.id}</span>
              </div>
            </div>

            <div className="space-y-3 text-xs bg-[#181828] p-4 rounded-xl border border-[#28283c]">
              <div className="flex justify-between">
                <span className="text-[#94a3b8]">Supplier ID:</span>
                <span className="text-white font-bold">{selectedOrder.supplier_id}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#94a3b8]">Status:</span>
                <span className="text-[#00ffcc] font-mono font-bold uppercase">{selectedOrder.status}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#94a3b8]">Total Quantity:</span>
                <span className="text-white font-bold">{selectedOrder.total_qty} units</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#94a3b8]">Created:</span>
                <span className="text-white font-mono">{new Date(selectedOrder.created_at).toLocaleString("en-IN")}</span>
              </div>
              {selectedOrder.notes && (
                <div className="pt-2 border-t border-[#242436]">
                  <span className="text-[#94a3b8] block mb-1">Notes:</span>
                  <p className="text-white">{selectedOrder.notes}</p>
                </div>
              )}
            </div>

            <div>
              <h4 className="text-xs font-mono uppercase tracking-wider text-[#94a3b8] font-bold mb-2">Item Breakdown</h4>
              <div className="space-y-1.5">
                {(selectedOrder.items as OrderItem[])?.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex justify-between items-center p-3 rounded-xl bg-[#181828] border border-[#28283c] text-xs font-mono"
                  >
                    <span className="text-[#00ffcc]">{item.sku}</span>
                    <span className="text-white font-bold">{item.quantity} units</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-end">
              <button
                onClick={() => setSelectedOrder(null)}
                className="px-5 py-2 rounded-xl bg-[#181826] hover:bg-[#202034] text-white text-xs font-medium border border-[#28283c]"
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
