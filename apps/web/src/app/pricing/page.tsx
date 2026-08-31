"use client";

import Link from "next/link";
import { useState } from "react";
import { Check, Sparkles, ShieldCheck, Zap, Crown } from "lucide-react";
import { FadeUp, StaggerContainer, StaggerItem } from "@/components/ScrollAnimations";

type Currency = "gbp" | "usd";

type Tier = {
  id: "starter" | "growth" | "enterprise";
  name: string;
  gbp: number;
  usd: number;
  tag: string | null;
  popular?: boolean;
  cta: string;
  href: string;
  features: string[];
};

const TIERS: Tier[] = [
  {
    id: "starter",
    name: "Starter",
    gbp: 49,
    usd: 59,
    tag: null,
    cta: "Start 14-Day Free Trial",
    href: "/sign-up?plan=starter",
    features: [
      "1 Voice Line",
      "500 call mins / month",
      "Google Sheets live mirror",
      "Email escalations",
      "UK GDPR retention controls",
      "Sub-second latency voice agent",
    ],
  },
  {
    id: "growth",
    name: "Growth",
    gbp: 149,
    usd: 179,
    tag: "Most Popular",
    popular: true,
    cta: "Start 14-Day Free Trial",
    href: "/sign-up?plan=growth",
    features: [
      "3 Voice Lines",
      "2,500 call mins / month",
      "Caller PIN verification (4-digit)",
      "Live Sheet Editing & tool-calling",
      "Priority support",
      "Amazon Connect telephony",
      "All Starter features",
    ],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    gbp: 399,
    usd: 479,
    tag: "For Scale",
    cta: "Contact Sales",
    href: "/sign-up?plan=enterprise",
    features: [
      "Unlimited voice lines",
      "Custom Lex STT models",
      "Dedicated UK DID",
      "24/7 SLA & on-call escalation",
      "Custom SLA escalations",
      "Dedicated success manager",
      "All Growth features",
    ],
  },
];

const FAQS = [
  {
    q: "How does the 14-day free trial work?",
    a: "Every workspace starts on a 14-day trial with full access — no card required. Add a payment method before the trial ends to keep your lines live. Cancel anytime from the Stripe Customer Portal.",
  },
  {
    q: "What counts as a call minute?",
    a: "Only connected call time. Ring time, failed verifications, and simulator sessions do not count toward your monthly minutes.",
  },
  {
    q: "Can I change plans or cancel anytime?",
    a: "Yes. Upgrade, downgrade, or cancel from Dashboard → Settings → Billing. Downgrades take effect at the next renewal; cancellation keeps your historical call data under your retention policy.",
  },
  {
    q: "Is VoxFlow UK GDPR compliant?",
    a: "Yes. Data residency is eu-west-2 (London), transcripts are purged on your retention schedule, and DSAR export/erasure plus the automated purge runner ship with every workspace.",
  },
  {
    q: "Which currencies and billing periods are supported?",
    a: "Billing is in £ GBP by default with $ USD shown for convenience. Monthly billing is standard; annual billing saves 20% on every tier.",
  },
];

export default function PricingPage() {
  const [currency, setCurrency] = useState<Currency>("gbp");
  const [annual, setAnnual] = useState(false);

  function displayPrice(tier: Tier) {
    const base = currency === "gbp" ? tier.gbp : tier.usd;
    const price = annual ? Math.round(base * 0.8) : base;
    const symbol = currency === "gbp" ? "£" : "$";
    return `${symbol}${price}`;
  }

  return (
    <div className="pt-[5.5rem] pb-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <FadeUp className="text-center max-w-3xl mx-auto mb-10 pt-12">
        <span className="font-label text-[#00ffcc] uppercase tracking-[0.2em] text-xs mb-4 block">
          ✦ Transparent UK Pricing
        </span>
        <h1 className="font-headline font-extrabold text-4xl sm:text-6xl tracking-tight text-[#e8e0f0] mb-4 leading-tight">
          Plans for every <span className="text-[#ff2d78] neon-text">operations team.</span>
        </h1>
        <p className="text-lg text-[#a098b0] font-body">
          Sub-second voice, Amazon Connect telephony, Google Sheets sync, and UK GDPR — billed in £ GBP or $ USD.
          14-day free trial on every tier.
        </p>
      </FadeUp>

      {/* Toggles */}
      <div className="flex flex-wrap items-center justify-center gap-4 mb-10">
        <div className="inline-flex rounded-full border border-[#302840]/50 bg-[#0f0f1a]/60 p-1">
          {(["gbp", "usd"] as Currency[]).map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setCurrency(c)}
              className={`rounded-full px-4 py-1.5 text-xs font-bold uppercase tracking-widest transition ${
                currency === c
                  ? "bg-[#ff2d78] text-white shadow"
                  : "text-[#a098b0] hover:text-[#e8e0f0]"
              }`}
            >
              {c === "gbp" ? "£ GBP" : "$ USD"}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={() => setAnnual((v) => !v)}
          className="inline-flex items-center gap-2 rounded-full border border-[#302840]/50 bg-[#0f0f1a]/60 px-4 py-2 text-xs font-bold text-[#e8e0f0] transition hover:border-[#00ffcc]/40"
          aria-pressed={annual}
        >
          <span
            className={`h-4 w-8 rounded-full p-0.5 transition ${annual ? "bg-[#00ffcc]" : "bg-[#302840]"}`}
          >
            <span
              className={`block h-3 w-3 rounded-full bg-white transition ${annual ? "translate-x-4" : ""}`}
            />
          </span>
          Annual <span className="text-[#00ffcc]">–20%</span>
        </button>
      </div>

      {/* Trust strip */}
      <div className="mx-auto mb-8 flex max-w-3xl flex-wrap justify-center gap-2 text-[11px] text-[#a098b0]">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-[#302840]/40 bg-[#141422]/60 px-3 py-1.5">
          <ShieldCheck size={12} className="text-[#00ffcc]" /> UK GDPR • eu-west-2
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-[#302840]/40 bg-[#141422]/60 px-3 py-1.5">
          <Zap size={12} className="text-[#ffe04a]" /> Sub-second latency
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-[#302840]/40 bg-[#141422]/60 px-3 py-1.5">
          <Crown size={12} className="text-[#ff2d78]" /> Stripe billing • VAT receipts
        </span>
      </div>

      <StaggerContainer className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-5 mb-12">
        {TIERS.map((tier) =>
          tier.popular ? (
            <div key={tier.id} className="relative bg-gradient-to-b from-[#ff2d78] to-[#00ffcc] p-[1px] rounded-2xl shadow-[0_0_40px_rgba(255,45,120,0.18)] scale-[1.02] z-10">
              <StaggerItem className="relative rounded-2xl bg-[#0f0f1c] p-6 sm:p-7 flex flex-col h-full">
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 whitespace-nowrap text-[10px] font-mono font-bold uppercase tracking-widest bg-[#ff2d78] text-white px-3.5 py-1 rounded-full shadow-[0_0_12px_rgba(255,45,120,0.6)]">
                  {tier.tag}
                </span>
            <div className="mb-1 flex items-center gap-2">
              <h3 className="font-headline font-bold text-xl text-[#f8fafc]">{tier.name}</h3>
              {tier.id === "enterprise" && <Sparkles size={14} className="text-[#f59e0b]" />}
              {tier.id === "starter" && <span className="text-[10px] font-mono tracking-widest uppercase text-[#64748b]">Single depot</span>}
            </div>
            <div className="flex items-baseline gap-1 mb-1">
              <span className="font-headline font-black text-4xl sm:text-5xl text-[#f8fafc]">{displayPrice(tier)}</span>
              <span className="text-xs font-mono text-[#64748b]">/ month</span>
            </div>
            <p className="mb-5 text-[11px] text-[#64748b]">{annual ? "Billed annually" : "Billed monthly"} • 14-day trial</p>
            <ul className="space-y-2.5 mb-7 flex-1">
              {tier.features.map((f) => (<li key={f} className="flex items-start gap-2.5 text-[13px] text-[#f8fafc]/90 leading-5"><Check size={14} className="text-[#00ffcc] mt-0.5 shrink-0" />{f}</li>))}
            </ul>
            <Link href={tier.href} className={`text-center font-bold text-sm px-5 py-3 rounded-xl transition-all active:scale-95 ${tier.popular ? "bg-[#ff2d78] text-white shadow-[0_0_25px_rgba(255,45,120,0.35)] hover:shadow-[0_0_30px_rgba(255,45,120,0.5)]" : "bg-white/[0.06] text-[#f8fafc] hover:bg-white/[0.10] border border-white/[0.07]"}`}>{tier.cta}</Link>
            <p className="mt-3 text-center text-[10px] text-[#64748b]">{currency === "gbp" ? "£ GBP" : "$ USD"} • Cancel in Stripe Portal</p>
              </StaggerItem>
            </div>
          ) : (
            <StaggerItem key={tier.id} className="relative rounded-2xl border border-white/[0.06] bg-[#0f0f1c]/80 backdrop-blur-2xl p-6 sm:p-7 flex flex-col hover:border-white/[0.10] transition-all">
              {tier.tag && (<span className="absolute -top-3 left-1/2 -translate-x-1/2 whitespace-nowrap text-[10px] font-mono font-bold uppercase tracking-widest bg-white/[0.08] text-[#94a3b8] border border-white/[0.07] px-3.5 py-1 rounded-full">{tier.tag}</span>)}
              <div className="mb-1 flex items-center gap-2"><h3 className="font-bold text-xl text-[#f8fafc]">{tier.name}</h3>{tier.id === "enterprise" && <Sparkles size={14} className="text-[#f59e0b]" />}</div>
              <div className="flex items-baseline gap-1 mb-1"><span className="font-black text-4xl sm:text-5xl text-[#f8fafc]">{displayPrice(tier)}</span><span className="text-xs font-mono text-[#64748b]">/ month</span></div>
              <p className="mb-5 text-[11px] text-[#64748b]">{annual ? "Billed annually" : "Billed monthly"} • 14-day trial</p>
              <ul className="space-y-2.5 mb-7 flex-1">{tier.features.map((f) => (<li key={f} className="flex items-start gap-2.5 text-[13px] text-[#f8fafc]/90 leading-5"><Check size={14} className="text-[#00ffcc] mt-0.5 shrink-0" />{f}</li>))}</ul>
              <Link href={tier.href} className="text-center font-bold text-sm px-5 py-3 rounded-xl bg-white/[0.06] text-[#f8fafc] hover:bg-white/[0.10] border border-white/[0.07] transition-all active:scale-95">{tier.cta}</Link>
              <p className="mt-3 text-center text-[10px] text-[#64748b]">{currency === "gbp" ? "£ GBP" : "$ USD"} • Cancel in Stripe Portal</p>
            </StaggerItem>
          )
        )}
      </StaggerContainer>

      <p className="mx-auto mb-16 max-w-3xl text-center text-xs leading-5 text-[#a098b0]">
        Prices exclude VAT where applicable. Invoices and VAT receipts are issued by Stripe. Need a custom volume,
        on-prem, or multi-region deployment?{" "}
        <Link href="/sign-up?plan=enterprise" className="text-[#00ffcc] hover:underline">
          Talk to sales
        </Link>
        .
      </p>

      {/* FAQ */}
      <div className="max-w-4xl mx-auto">
        <FadeUp>
          <h2 className="font-headline font-extrabold text-3xl text-[#e8e0f0] text-center mb-10">
            Frequently Asked Questions
          </h2>
        </FadeUp>
        <StaggerContainer className="space-y-4">
          {FAQS.map((faq) => (
            <StaggerItem key={faq.q}>
              <details className="rounded-xl border border-[#302840]/40 bg-[#141422]/70 group">
                <summary className="px-6 py-5 text-base font-headline font-semibold text-[#e8e0f0] cursor-pointer list-none flex items-center justify-between group-open:text-[#ff2d78] transition-colors">
                  {faq.q}
                  <span className="text-[#a098b0] group-open:rotate-180 transition-transform duration-200 text-lg">
                    ▾
                  </span>
                </summary>
                <div className="px-6 pb-5 text-sm text-[#a098b0] font-body leading-relaxed">{faq.a}</div>
              </details>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </div>
    </div>
  );
}
