"use client";

import Link from "next/link";
import { useState, useMemo } from "react";
import {
  Check,
  Sparkles,
  ShieldCheck,
  Zap,
  Crown,
  Calculator,
  ArrowRight,
  HelpCircle,
  CheckCircle2,
  Sliders,
  PhoneCall,
  Lock,
  Layers,
  FileSpreadsheet,
} from "lucide-react";
import CosmicStarfield from "@/components/CosmicStarfield";
import { FadeUp, StaggerContainer, StaggerItem } from "@/components/ScrollAnimations";

type Currency = "gbp" | "usd";

type Tier = {
  id: "starter" | "growth" | "enterprise";
  name: string;
  gbp: number;
  usd: number;
  minLimit: number;
  tag: string | null;
  popular?: boolean;
  cta: string;
  href: string;
  description: string;
  features: string[];
};

const TIERS: Tier[] = [
  {
    id: "starter",
    name: "Starter",
    gbp: 149,
    usd: 189,
    minLimit: 750,
    tag: null,
    description: "Ideal for small depots and local logistics teams starting voice automation.",
    cta: "Start 14-Day Free Trial",
    href: "/sign-up?plan=starter",
    features: [
      "1 Voice Line (Dedicated UK +44 20 DID)",
      "750 call mins / month included (15p/min overage)",
      "Google Sheets live 2-way mirror",
      "Email escalations & alerts",
      "UK GDPR retention controls (eu-west-2)",
      "~200ms turn, UK edge voice agent",
      "British English neural voice models",
    ],
  },
  {
    id: "growth",
    name: "Growth",
    gbp: 449,
    usd: 569,
    minLimit: 3000,
    tag: "Most Popular",
    popular: true,
    description: "For active transport operators handling high-frequency PO and delivery calls.",
    cta: "Start 14-Day Free Trial",
    href: "/sign-up?plan=growth",
    features: [
      "3 Concurrent Voice Lines",
      "3,000 call mins / month included (12p/min overage)",
      "Caller PIN verification (4-8 digits)",
      "Live Sheet Editing & ERP tool-calling",
      "Amazon Connect telephony routing",
      "Priority UK support (< 4h SLA)",
      "All Starter features included",
    ],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    gbp: 1499,
    usd: 1899,
    minLimit: 12000,
    tag: "For Scale",
    description: "High-volume fleet networks, bespoke multi-depot trunking, and 24/7 SLA.",
    cta: "Contact Solutions Team",
    href: "/contact?topic=Enterprise%20Plan",
    features: [
      "Unlimited concurrent voice lines",
      "12,000 call mins / month included (9p/min overage)",
      "Custom Lex STT acoustic models",
      "Dedicated UK DID (+44 20)",
      "24/7 SLA & dedicated on-call engineer",
      "Custom SLA escalations & webhooks",
      "Dedicated Solutions Architect",
      "All Growth features included",
    ],
  },
];

type ComparisonFeature = {
  name: string;
  starter: string | boolean;
  growth: string | boolean;
  enterprise: string | boolean;
  info?: string;
};

type ComparisonCategory = {
  category: string;
  features: ComparisonFeature[];
};

const COMPARISON_TABLE: ComparisonCategory[] = [
  {
    category: "Voice AI & Telephony",
    features: [
      { name: "Voice Lines", starter: "1 Line", growth: "3 Lines", enterprise: "Unlimited" },
      { name: "Monthly Included Minutes", starter: "750 mins", growth: "3,000 mins", enterprise: "12,000 mins included" },
      { name: "Voice Latency (~200ms Turn)", starter: true, growth: true, enterprise: true },
      { name: "UK English & Logistics Acoustics", starter: true, growth: true, enterprise: true },
      { name: "Custom Lex STT Acoustic Tuning", starter: false, growth: false, enterprise: true },
      { name: "Dedicated UK DID (+44)", starter: "Shared Pool", growth: "Included", enterprise: "Dedicated UK Trunk" },
    ],
  },
  {
    category: "Workflows & Integrations",
    features: [
      { name: "Google Sheets 2-Way Sync", starter: true, growth: true, enterprise: true },
      { name: "Caller PIN Verification (4-8 Digits)", starter: false, growth: true, enterprise: true },
      { name: "Live ERP & Database Tool Calling", starter: "Standard", growth: "Full", enterprise: "Custom API/VPC" },
      { name: "Email & Webhook Escalations", starter: "Email Only", growth: "Email + Webhooks", enterprise: "Custom SLA + On-Call" },
      { name: "Simulated Call Bench & Testing Sandbox", starter: true, growth: true, enterprise: true },
    ],
  },
  {
    category: "Security & Compliance",
    features: [
      { name: "UK GDPR & DPA Compliance", starter: true, growth: true, enterprise: true },
      { name: "Data Residency (London eu-west-2)", starter: true, growth: true, enterprise: true },
      { name: "Configurable Retention Windows", starter: "30 Days", growth: "90 Days", enterprise: "Custom Retention" },
      { name: "DSAR Export & One-Click Erasure", starter: true, growth: true, enterprise: true },
      { name: "PII Phone/Email Masking", starter: false, growth: true, enterprise: true },
    ],
  },
  {
    category: "Support & SLA",
    features: [
      { name: "Support Response Time", starter: "Within 24 Hours", growth: "Priority < 4 Hours", enterprise: "24/7 Dedicated On-Call" },
      { name: "Dedicated Solutions Architect", starter: false, growth: false, enterprise: true },
      { name: "Custom Telephony Onboarding", starter: "Self-Serve Docs", growth: "Assisted Setup", enterprise: "Full White-Glove" },
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
    a: "Only connected, productive call time with callers. Ring time, failed caller PIN verifications, and simulator testing sessions do not count toward your monthly allowance.",
  },
  {
    q: "Can I upgrade, downgrade, or cancel anytime?",
    a: "Yes. Upgrade or downgrade directly from Dashboard → Settings → Billing. Upgrades apply immediately with prorated billing. Cancellation retains your historical transcripts in accordance with your UK GDPR retention schedule.",
  },
  {
    q: "Is Voxflow UK GDPR and DPA compliant?",
    a: "Yes. Data residency is strictly eu-west-2 (London), transcripts are purged automatically on your retention schedule, and DSAR export/erasure plus the automated purge runner ship with every workspace.",
  },
  {
    q: "Which currencies and payment methods are supported?",
    a: "Billing is supported in £ GBP and $ USD. Payments are processed securely via Stripe, supporting all major credit/debit cards, BACS direct debit, and instant VAT invoice generation.",
  },
  {
    q: "What happens if we exceed our included monthly minutes?",
    a: "You will receive an alert at 80% and 100% capacity. Overages are billed at a flat rate (£0.04/min or $0.05/min), or you can upgrade to a higher tier with a single click.",
  },
];

export default function PricingPage() {
  const [currency, setCurrency] = useState<Currency>("gbp");
  const [annual, setAnnual] = useState(false);
  const [showMatrix, setShowMatrix] = useState(true);

  // Sizing Calculator state
  const [dailyCalls, setDailyCalls] = useState(40);
  const [callDuration, setCallDuration] = useState(2);

  const estimatedMonthlyMinutes = useMemo(() => {
    return Math.round(dailyCalls * callDuration * 22); // 22 working days/mo
  }, [dailyCalls, callDuration]);

  const recommendedTier = useMemo(() => {
    if (estimatedMonthlyMinutes <= 500) return "starter";
    if (estimatedMonthlyMinutes <= 2500) return "growth";
    return "enterprise";
  }, [estimatedMonthlyMinutes]);

  const estimatedHumanCost = useMemo(() => {
    // Average UK call handler cost @ £16/hr or ~$20/hr
    const hourlyRate = currency === "gbp" ? 16 : 20;
    const hours = estimatedMonthlyMinutes / 60;
    return Math.round(hours * hourlyRate * 1.35); // incl overheads
  }, [estimatedMonthlyMinutes, currency]);

  function displayPrice(tier: Tier) {
    const base = currency === "gbp" ? tier.gbp : tier.usd;
    const price = annual ? Math.round(base * 0.8) : base;
    const symbol = currency === "gbp" ? "£" : "$";
    return `${symbol}${price}`;
  }

  function renderFeatureValue(val: string | boolean) {
    if (typeof val === "boolean") {
      return val ? (
        <Check size={16} className="text-[#5EEAD4] mx-auto" />
      ) : (
        <span className="text-white/20">—</span>
      );
    }
    return <span className="text-xs text-white/90 font-mono font-medium">{val}</span>;
  }

  return (
    <div className="relative min-h-screen pt-[5.5rem] pb-24 px-4 sm:px-6 lg:px-8 text-white overflow-hidden">
      {/* Dynamic Cosmic Background */}
      <CosmicStarfield />

      {/* Layered Ambient Mesh Glows */}
      <div
        className="pointer-events-none fixed inset-0 z-0 overflow-hidden"
        aria-hidden="true"
      >
        <div className="absolute -top-40 left-1/3 h-[600px] w-[600px] rounded-full bg-[#5EEAD4]/10 blur-[150px]" />
        <div className="absolute top-1/2 -right-40 h-[600px] w-[600px] rounded-full bg-[#ff2d78]/10 blur-[160px]" />
        <div className="absolute bottom-10 -left-20 h-[500px] w-[500px] rounded-full bg-[#c084fc]/08 blur-[130px]" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto">
        {/* Hero Section */}
        <FadeUp className="text-center max-w-3xl mx-auto mb-10 pt-8">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-white/[0.08] bg-white/[0.02] text-xs font-mono tracking-widest text-[#5EEAD4] uppercase mb-4 backdrop-blur-md">
            <span className="h-1.5 w-1.5 rounded-full bg-[#5EEAD4] animate-pulse" />
            ✦ Transparent UK &amp; Global Pricing
          </div>
          <h1 className="font-headline font-extrabold text-4xl sm:text-6xl tracking-tight text-white mb-4 leading-tight">
            Plans for every <span className="text-[#5EEAD4]">operations team.</span>
          </h1>
          <p className="text-base sm:text-lg text-white/70 font-sans max-w-2xl mx-auto leading-relaxed">
            ~200ms turn, UK edge, Amazon Connect telephony, Google Sheets sync, and UK GDPR — billed in £ GBP or $ USD.
            14-day free trial on every tier.
          </p>
        </FadeUp>

        {/* Currency & Annual Toggle Controls */}
        <div className="flex flex-wrap items-center justify-center gap-4 mb-10">
          {/* Currency Toggle */}
          <div className="inline-flex rounded-full border border-white/[0.1] bg-[#070712]/80 backdrop-blur-md p-1 shadow-lg">
            {(["gbp", "usd"] as Currency[]).map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setCurrency(c)}
                className={`rounded-full px-4 py-1.5 text-xs font-bold uppercase tracking-widest transition-all font-mono cursor-pointer ${
                  currency === c
                    ? "bg-[#5EEAD4] text-[#030308] shadow-[0_0_15px_rgba(94,234,212,0.4)]"
                    : "text-white/60 hover:text-white"
                }`}
              >
                {c === "gbp" ? "£ GBP" : "$ USD"}
              </button>
            ))}
          </div>

          {/* Billing Switch */}
          <button
            type="button"
            onClick={() => setAnnual((v) => !v)}
            className="inline-flex items-center gap-2 rounded-full border border-white/[0.1] bg-[#070712]/80 backdrop-blur-md px-4 py-2 text-xs font-bold text-white transition hover:border-[#5EEAD4]/40 font-mono shadow-lg cursor-pointer"
            aria-pressed={annual}
          >
            <span
              className={`h-4 w-8 rounded-full p-0.5 transition-colors ${
                annual ? "bg-[#5EEAD4]" : "bg-white/20"
              }`}
            >
              <span
                className={`block h-3 w-3 rounded-full transition-transform ${
                  annual ? "translate-x-4 bg-[#030308]" : "bg-white"
                }`}
              />
            </span>
            <span>Annual Billing</span>
            <span className="rounded-full bg-[#5EEAD4]/20 border border-[#5EEAD4]/40 px-2 py-0.5 text-[10px] font-bold text-[#5EEAD4]">
              –20% Discount
            </span>
          </button>
        </div>

        {/* Trust Badges */}
        <div className="mx-auto mb-12 flex max-w-4xl flex-wrap justify-center gap-2.5 text-[11px] text-white/70 font-mono">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-[#0a0a14]/60 backdrop-blur-md px-3.5 py-1.5">
            <ShieldCheck size={13} className="text-[#5EEAD4]" /> UK GDPR • London eu-west-2
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-[#0a0a14]/60 backdrop-blur-md px-3.5 py-1.5">
            <Zap size={13} className="text-[#5EEAD4]" /> ~200ms Turn Latency
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-[#0a0a14]/60 backdrop-blur-md px-3.5 py-1.5">
            <Crown size={13} className="text-[#ffe04a]" /> Stripe Billing • VAT Invoices
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-[#0a0a14]/60 backdrop-blur-md px-3.5 py-1.5">
            <CheckCircle2 size={13} className="text-[#c084fc]" /> No Card Required for Trial
          </span>
        </div>

        {/* Pricing Cards Grid (3 Columns) */}
        <StaggerContainer className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6 mb-16 items-stretch">
          {TIERS.map((tier) => {
            const isRecommended = recommendedTier === tier.id;
            return (
              <StaggerItem
                key={tier.id}
                className={`relative rounded-3xl border p-7 sm:p-8 flex flex-col justify-between transition-all duration-300 backdrop-blur-xl ${
                  tier.popular
                    ? "border-[#5EEAD4]/60 bg-[#070714]/90 shadow-[0_0_40px_rgba(94,234,212,0.18)] hover:border-[#5EEAD4] scale-[1.02] z-20"
                    : "border-white/[0.1] bg-[#070712]/75 hover:border-[#5EEAD4]/40 hover:bg-[#070714]/90"
                } ${isRecommended && !tier.popular ? "ring-2 ring-[#5EEAD4]/40" : ""}`}
              >
                {/* Popular / Recommended Tag */}
                {tier.tag && (
                  <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 whitespace-nowrap text-[10px] font-mono font-bold uppercase tracking-widest bg-[#5EEAD4] text-[#030308] px-4 py-1 rounded-full shadow-[0_0_15px_rgba(94,234,212,0.6)]">
                    {tier.tag}
                  </span>
                )}

                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <h2 className="font-headline font-bold text-2xl text-white">
                      {tier.name}
                    </h2>
                    {tier.id === "enterprise" && (
                      <span className="p-1 rounded-lg bg-[#ffe04a]/10 border border-[#ffe04a]/30">
                        <Sparkles size={16} className="text-[#ffe04a]" />
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-white/60 font-sans mb-6 min-h-[32px] leading-relaxed">
                    {tier.description}
                  </p>

                  {/* Price Display */}
                  <div className="flex items-baseline gap-1.5 mb-1">
                    <span
                      id={`price-${tier.id}`}
                      data-currency={currency}
                      data-billing={annual ? "annual" : "monthly"}
                      className="font-headline font-black text-4xl sm:text-5xl text-white tracking-tight"
                    >
                      {displayPrice(tier)}
                    </span>
                    <span className="text-xs font-mono text-white/50">/ month</span>
                  </div>

                  <p className="mb-6 text-[11px] text-[#5EEAD4] font-mono">
                    {annual
                      ? `Billed annually (${displayPrice(tier)}/mo)`
                      : `Billed monthly (${displayPrice(tier)}/mo)`}{" "}
                    • 14-day free trial
                  </p>

                  {/* Features List */}
                  <div className="border-t border-white/[0.08] pt-6 mb-8">
                    <span className="text-[10px] font-mono uppercase tracking-widest text-white/40 block mb-3">
                      Included Capabilities
                    </span>
                    <ul className="space-y-3">
                      {tier.features.map((f) => (
                        <li
                          key={f}
                          className="flex items-start gap-2.5 text-xs sm:text-sm text-white/80 font-sans leading-relaxed"
                        >
                          <Check
                            size={16}
                            className="text-[#5EEAD4] mt-0.5 shrink-0"
                          />
                          <span>{f}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* CTA Button */}
                <div className="pt-2">
                  <Link
                    href={tier.href}
                    className={`w-full text-center font-headline font-bold text-sm px-6 py-3.5 min-h-[46px] rounded-xl transition-all duration-200 flex items-center justify-center gap-2 active:scale-95 ${
                      tier.popular
                        ? "bg-[#5EEAD4] text-[#030308] hover:shadow-[0_0_25px_rgba(94,234,212,0.5)]"
                        : "bg-white/[0.05] text-white hover:bg-white/[0.1] border border-white/[0.12] hover:border-[#5EEAD4]/30"
                    }`}
                  >
                    <span>{tier.cta}</span>
                    <ArrowRight size={15} />
                  </Link>

                  <p className="mt-3 text-center text-[10px] text-white/40 font-mono">
                    {currency === "gbp" ? "£ GBP" : "$ USD"} • 1-Click Cancel via Stripe
                  </p>
                </div>
              </StaggerItem>
            );
          })}
        </StaggerContainer>

        {/* Interactive Volume & Plan Recommendation Estimator (UX Sizing Tool) */}
        <FadeUp className="max-w-4xl mx-auto mb-16">
          <div className="rounded-3xl border border-white/[0.1] bg-[#070714]/80 backdrop-blur-2xl p-7 sm:p-10 shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 right-0 h-40 w-40 rounded-full bg-[#5EEAD4]/10 blur-[60px]" />

            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
              <div>
                <div className="inline-flex items-center gap-2 text-xs font-mono uppercase tracking-wider text-[#5EEAD4] mb-1">
                  <Calculator size={14} />
                  Call Volume &amp; ROI Estimator
                </div>
                <h3 className="font-headline font-bold text-2xl text-white">
                  Estimate your monthly operational needs
                </h3>
                <p className="text-xs text-white/60 font-sans">
                  Adjust sliders to calculate monthly minutes, recommended plan, and estimated cost savings.
                </p>
              </div>

              <div className="px-4 py-2 rounded-xl bg-white/[0.04] border border-white/[0.08] text-right">
                <span className="block text-[10px] font-mono uppercase text-white/40">
                  Recommended Tier
                </span>
                <span className="font-headline font-bold text-base text-[#5EEAD4] uppercase">
                  {recommendedTier}
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-8">
              {/* Slider 1: Calls per day */}
              <div className="space-y-3">
                <div className="flex justify-between items-center text-xs font-mono">
                  <span className="text-white/70 flex items-center gap-1.5">
                    <PhoneCall size={13} className="text-[#5EEAD4]" /> Daily Operational Calls
                  </span>
                  <span className="font-bold text-white text-sm bg-white/[0.05] px-2.5 py-1 rounded-md border border-white/[0.08]">
                    {dailyCalls} calls / day
                  </span>
                </div>
                <input
                  type="range"
                  min="5"
                  max="250"
                  step="5"
                  value={dailyCalls}
                  onChange={(e) => setDailyCalls(Number(e.target.value))}
                  className="w-full roi-slider"
                  aria-label="Daily operational calls slider"
                />
                <div className="flex justify-between text-[10px] font-mono text-white/40">
                  <span>5 calls</span>
                  <span>100 calls</span>
                  <span>250+ calls</span>
                </div>
              </div>

              {/* Slider 2: Average Call Duration */}
              <div className="space-y-3">
                <div className="flex justify-between items-center text-xs font-mono">
                  <span className="text-white/70 flex items-center gap-1.5">
                    <Sliders size={13} className="text-[#ff2d78]" /> Average Duration per Call
                  </span>
                  <span className="font-bold text-white text-sm bg-white/[0.05] px-2.5 py-1 rounded-md border border-white/[0.08]">
                    {callDuration} min{callDuration > 1 ? "s" : ""}
                  </span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="6"
                  step="0.5"
                  value={callDuration}
                  onChange={(e) => setCallDuration(Number(e.target.value))}
                  className="w-full roi-slider"
                  aria-label="Average duration per call slider"
                />
                <div className="flex justify-between text-[10px] font-mono text-white/40">
                  <span>1 min</span>
                  <span>3 mins</span>
                  <span>6 mins</span>
                </div>
              </div>
            </div>

            {/* Calculations Display Banner */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 p-5 rounded-2xl bg-[#030308]/80 border border-white/[0.08] text-center">
              <div>
                <span className="block text-[10px] font-mono uppercase text-white/40 mb-1">
                  Est. Monthly Minutes
                </span>
                <span className="font-headline font-bold text-xl text-white">
                  {estimatedMonthlyMinutes.toLocaleString()} mins
                </span>
              </div>

              <div className="border-t sm:border-t-0 sm:border-l border-white/[0.06] pt-3 sm:pt-0">
                <span className="block text-[10px] font-mono uppercase text-white/40 mb-1">
                  Voxflow Plan Cost
                </span>
                <span className="font-headline font-bold text-xl text-[#5EEAD4]">
                  {currency === "gbp" ? "£" : "$"}
                  {recommendedTier === "starter"
                    ? (currency === "gbp" ? (annual ? 119 : 149) : (annual ? 149 : 189))
                    : recommendedTier === "growth"
                    ? (currency === "gbp" ? (annual ? 359 : 449) : (annual ? 449 : 569))
                    : (currency === "gbp" ? (annual ? 1199 : 1499) : (annual ? 1499 : 1899))}
                  <span className="text-xs text-white/50 font-mono">/mo</span>
                </span>
              </div>

              <div className="border-t sm:border-t-0 sm:border-l border-white/[0.06] pt-3 sm:pt-0">
                <span className="block text-[10px] font-mono uppercase text-white/40 mb-1">
                  Traditional Staff Overhead
                </span>
                <span className="font-headline font-bold text-xl text-rose-300">
                  ~{currency === "gbp" ? "£" : "$"}{estimatedHumanCost.toLocaleString()}
                  <span className="text-xs text-white/40 font-mono">/mo</span>
                </span>
              </div>
            </div>
          </div>
        </FadeUp>

        {/* Comprehensive Feature Comparison Matrix */}
        <div className="max-w-6xl mx-auto mb-16">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-8">
            <div>
              <h2 className="font-headline font-bold text-2xl sm:text-3xl text-white">
                Detailed Feature Comparison
              </h2>
              <p className="text-xs sm:text-sm text-white/60 font-sans mt-1">
                Full transparent breakdown of technical specifications, compliance, and SLAs.
              </p>
            </div>

            <button
              type="button"
              onClick={() => setShowMatrix((v) => !v)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-white/[0.1] bg-white/[0.04] text-xs font-mono text-white/80 hover:text-white hover:border-[#5EEAD4]/40 transition cursor-pointer"
            >
              <Layers size={14} className="text-[#5EEAD4]" />
              {showMatrix ? "Hide Matrix" : "Expand Matrix"}
            </button>
          </div>

          {showMatrix && (
            <div className="rounded-3xl border border-white/[0.1] bg-[#070712]/80 backdrop-blur-2xl overflow-hidden shadow-2xl">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse min-w-[650px]">
                  <thead>
                    <tr className="border-b border-white/[0.08] bg-white/[0.02]">
                      <th className="py-4 px-6 text-xs font-mono uppercase tracking-wider text-white/50 w-2/5">
                        Features &amp; Specs
                      </th>
                      <th className="py-4 px-4 text-xs font-mono uppercase tracking-wider text-center text-white/80 w-1/5">
                        Starter
                      </th>
                      <th className="py-4 px-4 text-xs font-mono uppercase tracking-wider text-center text-[#5EEAD4] w-1/5 bg-[#5EEAD4]/[0.04]">
                        Growth ✦
                      </th>
                      <th className="py-4 px-4 text-xs font-mono uppercase tracking-wider text-center text-[#ffe04a] w-1/5">
                        Enterprise
                      </th>
                    </tr>
                  </thead>

                  <tbody>
                    {COMPARISON_TABLE.map((section, sIdx) => (
                      <tr key={sIdx} className="contents">
                        <td
                          colSpan={4}
                          className="py-3 px-6 bg-white/[0.03] text-xs font-mono font-bold uppercase tracking-widest text-[#5EEAD4] border-t border-b border-white/[0.06]"
                        >
                          {section.category}
                        </td>
                        {section.features.map((f, fIdx) => (
                          <tr
                            key={fIdx}
                            className="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors"
                          >
                            <td className="py-3.5 px-6 text-xs sm:text-sm text-white/80 font-sans">
                              {f.name}
                            </td>
                            <td className="py-3.5 px-4 text-center">
                              {renderFeatureValue(f.starter)}
                            </td>
                            <td className="py-3.5 px-4 text-center bg-[#5EEAD4]/[0.02]">
                              {renderFeatureValue(f.growth)}
                            </td>
                            <td className="py-3.5 px-4 text-center">
                              {renderFeatureValue(f.enterprise)}
                            </td>
                          </tr>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

        {/* Custom Volume & Enterprise Trunking Banner */}
        <div className="max-w-6xl mx-auto mb-20 rounded-3xl border border-[#5EEAD4]/30 bg-gradient-to-r from-[#5EEAD4]/[0.08] via-[#c084fc]/[0.05] to-transparent backdrop-blur-2xl p-8 sm:p-12 shadow-[0_0_50px_rgba(94,234,212,0.1)] relative overflow-hidden">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            <div className="lg:col-span-8 space-y-3">
              <span className="inline-flex items-center gap-2 font-mono text-xs text-[#5EEAD4] uppercase tracking-wider">
                <span className="h-2 w-2 rounded-full bg-[#5EEAD4] animate-ping" />
                Custom Deployments &amp; Multi-Depot Fleets
              </span>
              <h2 className="font-headline font-black text-2xl sm:text-4xl text-white tracking-tight">
                Need bespoke high-volume telephony or VPC peering?
              </h2>
              <p className="font-sans text-sm sm:text-base text-white/70 leading-relaxed max-w-2xl">
                We support 10,000+ monthly minutes, on-premises ERP connectors, dedicated London AWS eu-west-2 VPCs, and custom acoustic STT models tailored to regional depot accents.
              </p>
            </div>

            <div className="lg:col-span-4 flex flex-col sm:flex-row lg:flex-col gap-3 justify-center">
              <Link
                href="/contact?topic=Enterprise%20Plan"
                className="inline-flex items-center justify-center rounded-xl bg-[#5EEAD4] px-6 py-3.5 font-headline font-bold text-sm text-[#030308] hover:shadow-[0_0_25px_rgba(94,234,212,0.45)] transition active:scale-95 text-center"
              >
                Speak with Solutions Engineering →
              </Link>
              <a
                href="mailto:jeevesh2515@gmail.com?subject=VoxFlow%20Enterprise%20Volume%20Inquiry"
                className="inline-flex items-center justify-center rounded-xl border border-white/[0.12] bg-white/[0.04] px-6 py-3.5 font-headline font-bold text-xs text-white hover:bg-white/[0.08] transition text-center"
              >
                Email Lead Engineer Directly
              </a>
            </div>
          </div>
        </div>

        {/* FAQs */}
        <div className="max-w-4xl mx-auto">
          <FadeUp>
            <div className="text-center mb-10">
              <span className="font-mono text-xs text-[#5EEAD4] uppercase tracking-widest block mb-2">
                ✦ Clear Answers
              </span>
              <h2 className="font-headline font-extrabold text-3xl sm:text-4xl text-white">
                Frequently Asked Questions
              </h2>
            </div>
          </FadeUp>

          <StaggerContainer className="space-y-4">
            {FAQS.map((faq) => (
              <StaggerItem key={faq.q}>
                <details className="rounded-2xl border border-white/[0.08] bg-[#070712]/80 backdrop-blur-xl group transition-all duration-200 open:border-[#5EEAD4]/40 open:bg-[#070714]">
                  <summary className="px-6 py-5 text-base font-headline font-semibold text-white cursor-pointer list-none flex items-center justify-between group-open:text-[#5EEAD4] transition-colors select-none">
                    <span>{faq.q}</span>
                    <span className="text-white/40 group-open:rotate-180 transition-transform duration-200 text-lg ml-4">
                      ▾
                    </span>
                  </summary>
                  <div className="px-6 pb-6 pt-1 text-sm text-white/70 font-sans leading-relaxed border-t border-white/[0.04]">
                    {faq.a}
                  </div>
                </details>
              </StaggerItem>
            ))}
          </StaggerContainer>
        </div>
      </div>
    </div>
  );
}
