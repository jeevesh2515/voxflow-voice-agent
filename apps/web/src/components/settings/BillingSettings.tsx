"use client";

import { useState } from "react";
import useSWR from "swr";
import {
  CreditCard,
  Crown,
  ExternalLink,
  FileText,
  Loader2,
  ShieldCheck,
  Sparkles,
  AlertCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";
import type { BillingPlanTier, BillingStatus } from "@/lib/types";

const PLAN_LABELS: Record<string, string> = {
  starter: "Starter",
  growth: "Growth",
  enterprise: "Enterprise",
};

const STATUS_COLORS: Record<string, string> = {
  trialing: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  active: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
  past_due: "bg-red-500/15 text-red-300 border-red-500/30",
  canceled: "bg-slate-500/15 text-slate-400 border-slate-500/30",
  incomplete: "bg-orange-500/15 text-orange-300 border-orange-500/30",
};

function formatPence(pence: number | null, currency: string) {
  if (pence == null) return "—";
  const pounds = (pence / 100).toFixed(0);
  return currency === "gbp" ? `£${pounds}` : `$${pounds}`;
}

function formatDate(iso: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

export default function BillingSettings() {
  const { activeTenantId, activeTenant } = useTenant();
  const isOwner = activeTenant?.role === "owner";

  const {
    data: billing,
    error,
    isLoading,
    mutate,
  } = useSWR<BillingStatus>(
    activeTenantId ? ["billing-status", activeTenantId] : null,
    () => api.billingStatus(activeTenantId)
  );

  const [checkoutTier, setCheckoutTier] = useState<BillingPlanTier | null>(null);
  const [isCheckingOut, setIsCheckingOut] = useState(false);
  const [isOpeningPortal, setIsOpeningPortal] = useState(false);
  const [upgradeOpen, setUpgradeOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleCheckout(tier: BillingPlanTier) {
    if (!activeTenantId) return;
    setIsCheckingOut(true);
    setCheckoutTier(tier);
    setErrorMessage(null);
    try {
      const origin = window.location.origin;
      const result = await api.createBillingCheckout(activeTenantId, {
        plan_tier: tier,
        success_url: `${origin}/dashboard/settings?billing=success`,
        cancel_url: `${origin}/pricing`,
      });
      const url = result.checkout.checkout_url;
      if (url) {
        window.location.assign(url);
      } else {
        setErrorMessage("Checkout session created but no redirect URL was returned.");
      }
    } catch (err: unknown) {
      setErrorMessage(err instanceof Error ? err.message : "Checkout failed");
    } finally {
      setIsCheckingOut(false);
      setCheckoutTier(null);
    }
  }

  async function handlePortal() {
    if (!activeTenantId) return;
    setIsOpeningPortal(true);
    setErrorMessage(null);
    try {
      const result = await api.createBillingPortal(activeTenantId, window.location.href);
      if (result.portal.portal_url) window.location.href = result.portal.portal_url;
      else setErrorMessage("Portal session created but no redirect URL was returned.");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Portal failed";
      if (msg.includes("no_stripe_customer")) {
        setErrorMessage("Complete a checkout first — no payment method is on file yet.");
      } else {
        setErrorMessage(msg);
      }
    } finally {
      setIsOpeningPortal(false);
    }
  }

  if (isLoading) {
    return (
      <div className="overflow-hidden rounded-2xl border border-[#302840]/60 bg-[#141422]/40 p-6">
        <div className="flex items-center gap-2 text-sm text-[#a098b0]">
          <Loader2 size={16} className="animate-spin" /> Loading billing…
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="overflow-hidden rounded-2xl border border-red-500/30 bg-red-500/5 p-6">
        <p className="flex items-center gap-2 text-sm text-red-300">
          <AlertCircle size={16} /> Unable to load billing: {(error as Error).message}
        </p>
      </div>
    );
  }

  if (!billing) return null;

  const planLabel = PLAN_LABELS[billing.plan] ?? billing.plan;
  const statusStyle = STATUS_COLORS[billing.subscription_status] ?? STATUS_COLORS.trialing;

  return (
    <div className="overflow-hidden rounded-2xl border border-[#302840]/60 bg-[#141422]/40">
      <div className="flex items-center gap-3 border-b border-[#302840]/40 bg-[#0f0f1a]/60 px-5 py-4 sm:px-6">
        <CreditCard size={18} className="text-[#00ffcc]" />
        <div>
          <h2 className="text-sm font-bold text-[#e8e0f0]">Billing & Subscription</h2>
          <p className="text-[10px] text-[#a098b0]">
            Plan, renewal, invoices — powered by Stripe. Card data never touches VoxFlow.
          </p>
        </div>
        {billing.billing_mode === "sandbox" && (
          <span className="ml-auto rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-widest text-amber-300">
            Sandbox
          </span>
        )}
      </div>

      <div className="p-5 sm:p-6 space-y-6">
        {/* Current plan card */}
        <div className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-xl border border-[#302840]/40 bg-[#0f0f1a]/40 p-4">
            <p className="text-[10px] font-bold uppercase tracking-widest text-[#a098b0]">Current plan</p>
            <p className="mt-1 flex items-center gap-2 text-lg font-bold text-[#e8e0f0]">
              <Crown size={16} className="text-[#ff2d78]" /> {planLabel}
            </p>
            <p className="mt-1 text-xs text-[#a098b0]">
              {formatPence(billing.plan_amount_pence, billing.currency)} / month
            </p>
          </div>
          <div className="rounded-xl border border-[#302840]/40 bg-[#0f0f1a]/40 p-4">
            <p className="text-[10px] font-bold uppercase tracking-widest text-[#a098b0]">Status</p>
            <span
              className={`mt-2 inline-flex rounded-full border px-2.5 py-1 text-xs font-bold capitalize ${statusStyle}`}
            >
              {billing.subscription_status.replace("_", " ")}
            </span>
            {billing.cancel_at_period_end && (
              <p className="mt-2 text-[10px] text-amber-300">Cancels at period end</p>
            )}
          </div>
          <div className="rounded-xl border border-[#302840]/40 bg-[#0f0f1a]/40 p-4">
            <p className="text-[10px] font-bold uppercase tracking-widest text-[#a098b0]">Renews</p>
            <p className="mt-1 text-sm font-semibold text-[#e8e0f0]">{formatDate(billing.current_period_end)}</p>
            <p className="mt-1 text-[10px] text-[#a098b0]">
              {billing.has_stripe_customer ? "Stripe customer on file" : "No payment method yet"}
            </p>
          </div>
        </div>

        {errorMessage && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {errorMessage}
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={handlePortal}
            disabled={!isOwner || isOpeningPortal}
            className="inline-flex items-center gap-2 rounded-xl border border-[#302840] bg-[#1e1e30] px-4 py-2.5 min-h-[44px] text-xs font-bold text-[#e8e0f0] transition hover:border-[#00ffcc]/40 disabled:opacity-50"
          >
            {isOpeningPortal ? <Loader2 size={14} className="animate-spin" /> : <ExternalLink size={14} />}
            Manage Billing & Payment Methods
          </button>
          <button
            type="button"
            onClick={() => setUpgradeOpen((v) => !v)}
            disabled={!isOwner}
            className="inline-flex items-center gap-2 rounded-xl bg-[#ff2d78] px-4 py-2.5 min-h-[44px] text-xs font-bold text-white transition hover:bg-[#ff4470] disabled:opacity-50"
          >
            <Sparkles size={14} /> {upgradeOpen ? "Close" : "Change Plan"}
          </button>
          {!isOwner && (
            <span className="inline-flex items-center gap-1.5 text-[11px] text-[#a098b0]">
              <ShieldCheck size={12} /> Only workspace owners can manage billing.
            </span>
          )}
        </div>

        {/* Upgrade / downgrade */}
        {upgradeOpen && (
          <div className="grid gap-3 sm:grid-cols-3">
            {(["starter", "growth", "enterprise"] as BillingPlanTier[]).map((tier) => {
              const spec = billing.catalog?.[tier];
              const isCurrent = billing.plan === tier;
              return (
                <div
                  key={tier}
                  className={`rounded-xl border p-4 ${isCurrent ? "border-[#ff2d78]/40 bg-[#ff2d78]/5" : "border-[#302840]/40 bg-[#0f0f1a]/30"}`}
                >
                  <p className="text-xs font-bold uppercase tracking-widest text-[#e8e0f0]">
                    {PLAN_LABELS[tier]}
                  </p>
                  <p className="mt-1 text-sm font-semibold text-[#a098b0]">
                    {spec ? formatPence(spec.amount_pence, "gbp") : "—"} / mo
                  </p>
                  <p className="mt-1 text-[10px] text-[#a098b0]">
                    {spec
                      ? spec.voice_lines === 0
                        ? "Unlimited lines"
                        : `${spec.voice_lines} voice line${spec.voice_lines > 1 ? "s" : ""}`
                      : ""}
                  </p>
                  <button
                    type="button"
                    disabled={isCurrent || isCheckingOut}
                    onClick={() => handleCheckout(tier)}
                    className="mt-3 w-full rounded-lg bg-[#1e1e30] px-3 py-2 text-xs font-bold text-[#e8e0f0] transition hover:bg-[#28283e] disabled:opacity-50"
                  >
                    {isCheckingOut && checkoutTier === tier ? (
                      <span className="inline-flex items-center gap-1.5">
                        <Loader2 size={12} className="animate-spin" /> Redirecting…
                      </span>
                    ) : isCurrent ? (
                      "Current plan"
                    ) : (
                      `Switch to ${PLAN_LABELS[tier]}`
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* Invoice history */}
        <div>
          <h3 className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-[#e8e0f0]">
            <FileText size={14} className="text-[#a098b0]" /> Invoice history
          </h3>
          {billing.invoices.length === 0 ? (
            <p className="rounded-xl border border-dashed border-[#302840]/40 bg-[#0f0f1a]/20 px-4 py-6 text-center text-xs text-[#a098b0]">
              No invoices yet. Your first invoice appears after a successful payment.
            </p>
          ) : (
            <div className="overflow-hidden rounded-xl border border-[#302840]/40">
              <div className="max-h-64 overflow-auto">
                <table className="w-full text-left text-xs">
                  <thead className="sticky top-0 bg-[#0f0f1a] text-[10px] uppercase tracking-widest text-[#a098b0]">
                    <tr>
                      <th className="px-3 py-2.5 font-semibold">Date</th>
                      <th className="px-3 py-2.5 font-semibold">Amount</th>
                      <th className="px-3 py-2.5 font-semibold">Status</th>
                      <th className="px-3 py-2.5 font-semibold">Receipt</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#302840]/30">
                    {billing.invoices.map((inv) => (
                      <tr key={inv.stripe_invoice_id} className="text-[#e8e0f0]">
                        <td className="px-3 py-2.5 text-[#a098b0]">{formatDate(inv.paid_at ?? inv.created_at)}</td>
                        <td className="px-3 py-2.5 font-medium">
                          {(inv.amount_paid_cents / 100).toFixed(2)} {inv.currency.toUpperCase()}
                        </td>
                        <td className="px-3 py-2.5">
                          <span className="rounded-full bg-[#1e1e30] px-2 py-1 text-[10px] font-bold capitalize">
                            {inv.status}
                          </span>
                        </td>
                        <td className="px-3 py-2.5">
                          {inv.invoice_pdf_url ? (
                            <a
                              href={inv.invoice_pdf_url}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1 text-[#00ffcc] hover:underline"
                            >
                              PDF <ExternalLink size={10} />
                            </a>
                          ) : inv.hosted_invoice_url ? (
                            <a
                              href={inv.hosted_invoice_url}
                              target="_blank"
                              rel="noreferrer"
                              className="inline-flex items-center gap-1 text-[#00ffcc] hover:underline"
                            >
                              View <ExternalLink size={10} />
                            </a>
                          ) : (
                            <span className="text-[#a098b0]">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        <p className="text-[10px] leading-4 text-[#a098b0]">
          Billing is processed by Stripe. VoxFlow never stores card numbers — payment methods, VAT receipts, and
          cancellation are managed inside the Stripe Customer Portal.
        </p>
      </div>
    </div>
  );
}
