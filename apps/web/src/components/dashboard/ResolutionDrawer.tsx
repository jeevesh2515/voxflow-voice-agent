"use client";

import React, { useState } from "react";
import {
  X,
  CheckCircle2,
  AlertTriangle,
  Clock,
  User,
  Phone,
  ShieldAlert,
  FileText,
  Activity,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import type { Call, EscalationPriority, ResolutionCategory } from "@/lib/types";
import { api } from "@/lib/api";

interface ResolutionDrawerProps {
  call: Call | null;
  isOpen: boolean;
  onClose: () => void;
  onResolved: (updatedCall: Call) => void;
  tenantId: string;
}

const CATEGORY_LABELS: Record<ResolutionCategory, string> = {
  callback_completed: "Callback Completed",
  order_updated: "Order / Shipment Corrected",
  refund_issued: "Refund / Credit Issued",
  quote_sent: "Custom Quote / Pricing Sent",
  technical_fixed: "Technical / System Issue Fixed",
  duplicate_or_invalid: "Duplicate / Invalid Escalation",
  other: "Other Operator Resolution",
};

export function ResolutionDrawer({
  call,
  isOpen,
  onClose,
  onResolved,
  tenantId,
}: ResolutionDrawerProps) {
  const [resolutionStatus, setResolutionStatus] = useState<"resolved" | "dismissed">("resolved");
  const [category, setCategory] = useState<ResolutionCategory>("callback_completed");
  const [notes, setNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState<number>(0);

  React.useEffect(() => {
    setCurrentTime(Date.now());
  }, []);

  if (!isOpen || !call) return null;

  const isBreached = () => {
    if (!call.sla_due_at || currentTime === 0) return false;
    if (call.escalation_status === "resolved" || call.escalation_status === "dismissed") return false;
    return new Date(call.sla_due_at).getTime() < currentTime;
  };

  const getPriorityBadge = (p?: EscalationPriority) => {
    switch (p) {
      case "critical":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
            <AlertTriangle className="w-3 h-3" /> Critical Priority
          </span>
        );
      case "high":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <AlertTriangle className="w-3 h-3" /> High Priority
          </span>
        );
      case "low":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Clock className="w-3 h-3" /> Low Priority
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Clock className="w-3 h-3" /> Medium Priority
          </span>
        );
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!notes.trim()) {
      setError("Please provide closing resolution notes.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const updated = await api.resolveEscalation(tenantId, call.id, {
        status: resolutionStatus,
        resolution_category: category,
        staff_resolution: notes.trim(),
      });
      onResolved(updated);
      onClose();
    } catch (err: any) {
      setError(err?.message || "Failed to resolve escalation ticket.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm flex justify-end animate-in fade-in duration-200">
      <div className="w-full max-w-2xl bg-zinc-950 border-l border-zinc-800 text-zinc-100 h-full overflow-y-auto flex flex-col shadow-2xl">
        {/* Header */}
        <div className="p-6 border-b border-zinc-800/80 bg-zinc-900/40 sticky top-0 z-10 backdrop-blur">
          <div className="flex items-start justify-between">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-zinc-400 uppercase tracking-wider">
                  Ticket #{call.id.slice(-8)}
                </span>
                {getPriorityBadge(call.escalation_priority)}
                {isBreached() && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-950 text-rose-300 border border-rose-800/80 animate-pulse">
                    <ShieldAlert className="w-3 h-3" /> SLA Breached
                  </span>
                )}
              </div>
              <h2 className="text-lg font-semibold text-zinc-100 flex items-center gap-2">
                {call.caller_name || "Unknown Caller"}
                <span className="text-xs font-normal text-zinc-400">({call.caller_phone})</span>
              </h2>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/80 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-6 flex-1">
          {/* Caller Context Card */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-4 rounded-xl bg-zinc-900/60 border border-zinc-800 text-xs">
            <div>
              <span className="text-zinc-400 block mb-0.5">Intent</span>
              <span className="font-medium text-zinc-200">{call.intent || "General Inquiry"}</span>
            </div>
            <div>
              <span className="text-zinc-400 block mb-0.5">Call Outcome</span>
              <span className="font-medium text-zinc-200">{call.outcome || "Escalated"}</span>
            </div>
            <div>
              <span className="text-zinc-400 block mb-0.5">Target SLA Due</span>
              <span className="font-medium text-zinc-200">
                {call.sla_due_at ? new Date(call.sla_due_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "N/A"}
              </span>
            </div>
            {call.assigned_to_user_id && (
              <div>
                <span className="text-zinc-400 block mb-0.5">Assigned Operator</span>
                <span className="font-medium text-indigo-300">{call.assigned_to_user_id}</span>
              </div>
            )}
            <div>
              <span className="text-zinc-400 block mb-0.5">Caller Sentiment</span>
              <span className={`font-medium capitalize ${call.satisfaction === "unhappy" ? "text-amber-400" : "text-zinc-200"}`}>
                {call.satisfaction || "Neutral"}
              </span>
            </div>
            <div>
              <span className="text-zinc-400 block mb-0.5">Call Duration</span>
              <span className="font-medium text-zinc-200">{call.duration_sec || 0}s</span>
            </div>
          </div>

          {/* Reason & Solution Summary */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-zinc-400" />
              Agent Escalation Reason & Solution
            </h3>
            <div className="p-4 rounded-xl bg-zinc-900/40 border border-zinc-800/80 space-y-2 text-sm">
              <div>
                <span className="text-xs font-medium text-zinc-400 block">Identified Reason:</span>
                <p className="text-zinc-200 text-xs mt-0.5">{call.reason || "Customer requested human supervisor support."}</p>
              </div>
              {call.solution && (
                <div>
                  <span className="text-xs font-medium text-zinc-400 block">Proposed Action:</span>
                  <p className="text-zinc-300 text-xs mt-0.5">{call.solution}</p>
                </div>
              )}
            </div>
          </div>

          {/* Call Transcript Accordion / Snippet */}
          {call.transcript && call.transcript.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-400 flex items-center gap-1.5">
                <MessageSquare className="w-3.5 h-3.5 text-zinc-400" />
                Live Call Transcript ({call.transcript.length} turns)
              </h3>
              <div className="max-h-48 overflow-y-auto space-y-2 p-3 rounded-xl bg-zinc-900/30 border border-zinc-800/80">
                {call.transcript.map((t, idx) => (
                  <div
                    key={idx}
                    className={`p-2.5 rounded-lg text-xs ${
                      t.role === "caller"
                        ? "bg-zinc-800/60 text-zinc-200 border-l-2 border-indigo-400 ml-4"
                        : "bg-zinc-900/80 text-zinc-300 border-l-2 border-emerald-400 mr-4"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1 opacity-75 font-mono text-[10px]">
                      <span>{t.role === "caller" ? "Caller" : "AI Agent"}</span>
                      <span>{new Date(t.at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</span>
                    </div>
                    <p className="leading-relaxed">{t.text}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Operator Resolution Form */}
          <form onSubmit={handleSubmit} className="space-y-4 pt-2 border-t border-zinc-800/80">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-zinc-300 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                Closed-Loop Resolution
              </h3>
            </div>

            {error && (
              <div className="p-3 rounded-lg bg-red-950/50 border border-red-800/80 text-red-300 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Resolution Type / Status */}
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setResolutionStatus("resolved")}
                className={`flex items-center justify-center gap-2 p-2.5 rounded-lg border text-xs font-medium transition-all ${
                  resolutionStatus === "resolved"
                    ? "bg-emerald-500/10 border-emerald-500/50 text-emerald-300 shadow-sm"
                    : "bg-zinc-900/40 border-zinc-800 text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                Mark Resolved
              </button>
              <button
                type="button"
                onClick={() => setResolutionStatus("dismissed")}
                className={`flex items-center justify-center gap-2 p-2.5 rounded-lg border text-xs font-medium transition-all ${
                  resolutionStatus === "dismissed"
                    ? "bg-zinc-800 border-zinc-600 text-zinc-200 shadow-sm"
                    : "bg-zinc-900/40 border-zinc-800 text-zinc-400 hover:text-zinc-200"
                }`}
              >
                <X className="w-3.5 h-3.5" />
                Dismiss / Invalid
              </button>
            </div>

            {/* Resolution Category Dropdown */}
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1">
                Resolution Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as ResolutionCategory)}
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-2 text-xs text-zinc-200 focus:outline-none focus:border-indigo-500 transition-colors"
              >
                {Object.entries(CATEGORY_LABELS).map(([catKey, label]) => (
                  <option key={catKey} value={catKey}>
                    {label}
                  </option>
                ))}
              </select>
            </div>

            {/* Operator Closing Notes */}
            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1">
                Operator Action & Closing Notes <span className="text-red-400">*</span>
              </label>
              <textarea
                rows={3}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Detail the actions taken with the supplier/customer (e.g. called back and updated dispatch address)..."
                className="w-full bg-zinc-900 border border-zinc-800 rounded-lg p-3 text-xs text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
              />
            </div>

            {/* Action Buttons */}
            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                disabled={isSubmitting}
                className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-300 text-xs font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium shadow-md transition-all disabled:opacity-50"
              >
                {isSubmitting ? (
                  <Activity className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <CheckCircle2 className="w-3.5 h-3.5" />
                )}
                Confirm Resolution
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
