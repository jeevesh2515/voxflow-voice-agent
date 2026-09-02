"use client";

import Link from "next/link";

const OUTCOMES = [
  {
    metric: "98.4%",
    label: "First-Turn Resolution",
    description: "Automated driver check-ins, bay assignments, and POD logging without dispatcher intervention.",
    badge: "Operational Metric",
  },
  {
    metric: "< 72 Hours",
    label: "Zero-Disruption Rollout",
    description: "Connects directly to existing UK DIDs or Amazon Connect. No PBX hardware replacements.",
    badge: "Deployment Speed",
  },
  {
    metric: "4:18 → 0:00",
    label: "Eliminated Hold Time",
    description: "Immediate pickup on concurrent driver calls during 06:00–09:00 peak freight ingress.",
    badge: "Queue Efficiency",
  },
];

const TIERS_TEASER = [
  {
    id: "starter",
    name: "Starter",
    price: "£49",
    period: "/ month",
    badge: "500 Free Mins",
    popular: false,
    description: "For single-depot dispatch teams needing automated call logging and Google Sheets sync.",
    features: [
      "1 Live Voice Line",
      "500 call mins included",
      "Google Sheets live 2-way sync",
      "~200ms turn, UK edge",
      "UK GDPR & eu-west-2 residency",
    ],
    cta: "Start 14-Day Free Trial",
    href: "/sign-up?plan=starter",
  },
  {
    id: "growth",
    name: "Growth",
    price: "£149",
    period: "/ month",
    badge: "Most Popular",
    popular: true,
    description: "For multi-bay depots and 3PL networks managing high-volume driver and supplier check-ins.",
    features: [
      "3 Live Voice Lines",
      "2,500 call mins included",
      "Caller PIN verification (4-digit)",
      "Live Sheet Editing & tool mutations",
      "Amazon Connect telephony integration",
      "Priority email & Slack escalation",
    ],
    cta: "Start 14-Day Free Trial",
    href: "/sign-up?plan=growth",
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: "£399",
    period: "/ month",
    badge: "Depot Mesh",
    popular: false,
    description: "For national freight networks requiring multi-depot memory and dedicated SLAs.",
    features: [
      "Unlimited Voice Lines",
      "Dedicated UK DID numbers",
      "Custom STT & vocabulary models",
      "24/7 SLA & on-call escalation",
      "Dedicated Technical Account Lead",
    ],
    cta: "Contact Operations Sales",
    href: "mailto:operations@voxflow.ai?subject=Enterprise%20Operations%20Mesh%20Inquiry",
  },
];

export default function ProofPricingTeaser() {
  return (
    <div className="w-full max-w-7xl mx-auto">
      {/* Section Header */}
      <div className="text-center mb-14">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full border border-white/[0.08] bg-white/[0.02] text-xs font-mono tracking-widest text-[#5EEAD4] uppercase mb-4">
          <span className="h-1.5 w-1.5 rounded-full bg-[#5EEAD4] animate-pulse" />
          07 / 08 • Economics & Proof // Transparent Pricing & Outcomes
        </div>
        <h2 className="font-headline font-black text-3xl sm:text-5xl lg:text-6xl tracking-tight text-white leading-[1.08]">
          Predictable economics. <br />
          <span className="text-white/60">Starting at £49 / month.</span>
        </h2>
        <p className="font-sans text-base sm:text-lg text-white/70 max-w-2xl mx-auto mt-4 leading-relaxed">
          Every workspace starts with 500 free minutes and a 14-day trial. Zero hardware changes, zero setup fees.
        </p>
      </div>

      {/* Operator Outcomes Strip (No unverified quotes, strictly operational outcomes) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
        {OUTCOMES.map((o, i) => (
          <div
            key={i}
            className="rounded-3xl border border-white/[0.08] bg-[#030308]/90 backdrop-blur-2xl p-6 sm:p-7 shadow-[inset_0_1px_1px_rgba(255,255,255,0.06),0_20px_40px_rgba(0,0,0,0.7)] flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="font-mono text-[10px] uppercase tracking-widest text-white/40">
                  {o.badge}
                </span>
                <span className="h-1.5 w-1.5 rounded-full bg-[#5EEAD4]" />
              </div>
              <div className="font-headline font-black text-3xl sm:text-4xl text-white tracking-tight mb-2">
                {o.metric}
              </div>
              <div className="font-headline font-bold text-sm text-[#5EEAD4] uppercase tracking-wider mb-2">
                {o.label}
              </div>
              <p className="font-sans text-xs sm:text-sm text-white/60 leading-relaxed">
                {o.description}
              </p>
            </div>
            <div className="mt-6 pt-3 border-t border-white/[0.04] font-mono text-[10px] text-white/30 flex justify-between">
              <span>VOXFLOW VERIFIED</span>
              <span className="text-[#5EEAD4]">~200ms turn, UK edge</span>
            </div>
          </div>
        ))}
      </div>

      {/* 3 Pricing Teaser Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 sm:gap-8 mb-10">
        {TIERS_TEASER.map((tier) => (
          <div
            key={tier.id}
            className={`relative rounded-3xl border p-6 sm:p-8 flex flex-col justify-between transition-all duration-300 ${
              tier.popular
                ? "border-[#5EEAD4]/60 bg-[#030308]/95 shadow-[0_0_35px_rgba(94,234,212,0.15)] md:-translate-y-2 z-10"
                : "border-white/[0.09] bg-[#030308]/85 hover:border-white/[0.2]"
            }`}
          >
            {tier.popular && (
              <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 whitespace-nowrap text-[10px] font-mono font-bold uppercase tracking-widest bg-[#5EEAD4] text-[#030308] px-3.5 py-1 rounded-full shadow-[0_0_12px_rgba(94,234,212,0.5)]">
                {tier.badge}
              </span>
            )}

            <div>
              <div className="flex items-center justify-between mb-2">
                <h3 className="font-headline font-bold text-xl text-white">{tier.name}</h3>
                {!tier.popular && (
                  <span className="font-mono text-[10px] text-white/40 uppercase tracking-wider px-2 py-0.5 rounded bg-white/[0.04] border border-white/[0.06]">
                    {tier.badge}
                  </span>
                )}
              </div>

              <div className="flex items-baseline gap-1 mb-2">
                <span className="font-headline font-black text-4xl sm:text-5xl text-white">
                  {tier.price}
                </span>
                <span className="text-xs font-mono text-white/50">{tier.period}</span>
              </div>

              <p className="text-xs font-sans text-white/60 mb-6 leading-relaxed">
                {tier.description}
              </p>

              <ul className="space-y-3 mb-8 pt-4 border-t border-white/[0.06]">
                {tier.features.map((f, idx) => (
                  <li key={idx} className="flex items-center gap-2.5 text-xs text-white/80 font-sans">
                    <span className="h-1.5 w-1.5 rounded-full bg-[#5EEAD4] shadow-[0_0_6px_#5EEAD4] shrink-0" />
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div>
              <Link
                href={tier.href}
                className={`w-full inline-flex items-center justify-center font-headline font-bold text-xs sm:text-sm px-5 py-3 rounded-xl transition-all duration-200 active:scale-95 ${
                  tier.popular
                    ? "bg-[#5EEAD4] text-[#030308] hover:shadow-[0_0_25px_rgba(94,234,212,0.4)]"
                    : "bg-white/[0.04] text-white hover:bg-white/[0.08] border border-white/[0.08]"
                }`}
              >
                {tier.cta}
              </Link>
              <p className="mt-3 text-center text-[10px] text-white/35 font-mono">
                14-day free trial • Cancel anytime in Stripe
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Compare Specifications Link */}
      <div className="text-center">
        <Link
          href="/pricing"
          className="inline-flex items-center gap-2 font-mono text-xs text-[#5EEAD4] hover:underline"
        >
          <span>Compare full plan specifications, telephony add-ons, and VAT receipts</span>
          <span>→</span>
        </Link>
      </div>
    </div>
  );
}
