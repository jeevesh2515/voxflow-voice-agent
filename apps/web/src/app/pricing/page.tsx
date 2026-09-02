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
      "~200ms turn, UK edge voice agent",
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
    <div className="pt-[5.5rem] pb-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-white relative z-10">
      <FadeUp className="text-center max-w-3xl mx-auto mb-10 pt-12">
        <span className="font-mono text-[#5EEAD4] uppercase tracking-[0.2em] text-xs mb-4 block">
          ✦ Transparent UK Pricing
        </span>
        <h1 className="font-headline font-extrabold text-4xl sm:text-6xl tracking-tight text-white mb-4 leading-tight">
          Plans for every <span className="text-[#5EEAD4]">operations team.</span>
        </h1>
        <p className="text-lg text-white/70 font-sans">
          ~200ms turn, UK edge, Amazon Connect telephony, Google Sheets sync, and UK GDPR — billed in £ GBP or $ USD.
          14-day free trial on every tier.
        </p>
      </FadeUp>

      {/* Toggles */}
      <div className="flex flex-wrap items-center justify-center gap-4 mb-10">
        <div className="inline-flex rounded-full border border-white/[0.08] bg-white/[0.02] p-1">
          {(["gbp", "usd"] as Currency[]).map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setCurrency(c)}
              className={`rounded-full px-4 py-1.5 text-xs font-bold uppercase tracking-widest transition font-mono ${
                currency === c
                  ? "bg-[#5EEAD4] text-[#030308] shadow"
                  : "text-white/60 hover:text-white"
              }`}
            >
              {c === "gbp" ? "£ GBP" : "$ USD"}
            </button>
          ))}
        </div>
        <button
          type="button"
          onClick={() => setAnnual((v) => !v)}
          className="inline-flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.02] px-4 py-2 text-xs font-bold text-white transition hover:border-[#5EEAD4]/40 font-mono"
          aria-pressed={annual}
        >
          <span
            className={`h-4 w-8 rounded-full p-0.5 transition ${annual ? "bg-[#5EEAD4]" : "bg-white/20"}`}
          >
            <span
              className={`block h-3 w-3 rounded-full bg-white transition ${annual ? "translate-x-4 bg-[#030308]" : ""}`}
            />
          </span>
          Annual <span className="text-[#5EEAD4]">–20%</span>
        </button>
      </div>

      {/* Trust strip */}
      <div className="mx-auto mb-8 flex max-w-3xl flex-wrap justify-center gap-2 text-[11px] text-white/60 font-mono">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.06] bg-white/[0.02] px-3 py-1.5">
          <ShieldCheck size={12} className="text-[#5EEAD4]" /> UK GDPR • eu-west-2
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.06] bg-white/[0.02] px-3 py-1.5">
          <Zap size={12} className="text-[#5EEAD4]" /> ~200ms turn, UK edge
        </span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.06] bg-white/[0.02] px-3 py-1.5">
          <Crown size={12} className="text-[#5EEAD4]" /> Stripe billing • VAT receipts
        </span>
      </div>

      {/* Pricing Cards — 3 Columns */}
      <StaggerContainer className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6 mb-14">
        {TIERS.map((tier) => (
          <StaggerItem
            key={tier.id}
            className={`relative rounded-2xl border p-6 sm:p-7 flex flex-col transition-all duration-300 ${
              tier.popular
                ? "border-[#5EEAD4]/60 bg-[#0a0a12]/90 shadow-[0_0_35px_rgba(94,234,212,0.15)] hover:border-[#5EEAD4] scale-[1.02] z-10"
                : "border-white/[0.08] bg-[#0a0a12]/60 hover:border-[#5EEAD4]/40"
            }`}
          >
            {tier.tag && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 whitespace-nowrap text-[10px] font-mono font-bold uppercase tracking-widest bg-[#5EEAD4] text-[#030308] px-3.5 py-1 rounded-full shadow-[0_0_12px_rgba(94,234,212,0.5)]">
                {tier.tag}
              </span>
            )}
            <div className="mb-1 flex items-center gap-2">
              <h3 className="font-headline font-bold text-xl text-white">{tier.name}</h3>
              {tier.id === "enterprise" && <Sparkles size={14} className="text-[#ffe04a]" />}
            </div>
            <div className="flex items-baseline gap-1 mb-1">
              <span
                id={`price-${tier.id}`}
                data-currency={currency}
                data-billing={annual ? "annual" : "monthly"}
                className="font-headline font-black text-4xl sm:text-5xl text-white"
              >
                {displayPrice(tier)}
              </span>
              <span className="text-xs font-mono text-white/50">/ month</span>
            </div>
            <p className="mb-5 text-[11px] text-white/50 font-mono">
              {annual ? `Billed annually (${displayPrice(tier)}/mo)` : `Billed monthly (${displayPrice(tier)}/mo)`} • 14-day free trial
            </p>
            <ul className="space-y-3 mb-8 flex-1">
              {tier.features.map((f) => (
                <li
                  key={f}
                  className="flex items-start gap-2.5 text-xs sm:text-sm text-white/80 font-sans"
                >
                  <Check size={15} className="text-[#5EEAD4] mt-0.5 shrink-0" />
                  {f}
                </li>
              ))}
            </ul>
            <Link
              href={tier.href}
              className={`text-center font-headline font-bold text-xs sm:text-sm px-5 py-3 min-h-[44px] rounded-xl transition-all duration-200 active:scale-95 ${
                tier.popular
                  ? "bg-[#5EEAD4] text-[#030308] hover:shadow-[0_0_25px_rgba(94,234,212,0.4)]"
                  : "bg-white/[0.04] text-white hover:bg-white/[0.08] border border-white/[0.08]"
              }`}
            >
              {tier.cta}
            </Link>
            <p className="mt-3 text-center text-[10px] text-white/40 font-mono">
              {currency === "gbp" ? "£ GBP" : "$ USD"} • Cancel in Stripe Portal
            </p>
          </StaggerItem>
        ))}
      </StaggerContainer>

      <p className="mx-auto mb-16 max-w-3xl text-center text-xs leading-5 text-white/50 font-mono">
        Prices exclude VAT where applicable. Invoices and VAT receipts are issued by Stripe. Need a custom volume,
        on-prem, or multi-region deployment?{" "}
        <Link href="/sign-up?plan=enterprise" className="text-[#5EEAD4] hover:underline">
          Talk to sales
        </Link>
        .
      </p>

      {/* FAQ */}
      <div className="max-w-4xl mx-auto">
        <FadeUp>
          <h2 className="font-headline font-extrabold text-3xl text-white text-center mb-10">
            Frequently Asked Questions
          </h2>
        </FadeUp>
        <StaggerContainer className="space-y-4">
          {FAQS.map((faq) => (
            <StaggerItem key={faq.q}>
              <details className="rounded-xl border border-white/[0.08] bg-[#0a0a12]/80 group">
                <summary className="px-6 py-5 text-base font-headline font-semibold text-white cursor-pointer list-none flex items-center justify-between group-open:text-[#5EEAD4] transition-colors">
                  {faq.q}
                  <span className="text-white/40 group-open:rotate-180 transition-transform duration-200 text-lg">
                    ▾
                  </span>
                </summary>
                <div className="px-6 pb-5 text-sm text-white/60 font-sans leading-relaxed">{faq.a}</div>
              </details>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </div>
    </div>
  );
}
