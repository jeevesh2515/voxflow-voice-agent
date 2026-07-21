import Link from "next/link";
import { Check } from "lucide-react";
import { FadeUp, StaggerContainer, StaggerItem } from "@/components/ScrollAnimations";

const tiers = [
  {
    id: "starter",
    name: "Starter Pilot",
    price: "$0",
    period: "/month",
    tag: null,
    features: [
      "1 Active Workspace",
      "Up to 100 calls/month",
      "Hindi-English & Regional Dialects",
      "Basic Call Log & Analytics",
      "Standard Support",
    ],
    missing: [
      "Real-time Order & PO Capture",
      "Custom Voice Tone",
      "REST & Webhooks API",
      "Dedicated Infrastructure",
    ],
    cta: "Start Free Pilot",
    href: "/sign-up?plan=starter",
    popular: false,
  },
  {
    id: "pro",
    name: "Pro Operations",
    price: "$49",
    period: "/month",
    tag: "Most Popular",
    features: [
      "3 Workspaces",
      "Up to 1,500 calls/month",
      "Real-time Order & PO Capture",
      "Advanced Analytics & Transcripts",
      "Priority Email & Chat Support",
      "Webhook & Database Export",
    ],
    missing: [
      "Custom Voice Tone",
      "REST & Webhooks API",
    ],
    cta: "Start 14-Day Trial",
    href: "/sign-up?plan=pro",
    popular: true,
  },
  {
    id: "scale",
    name: "Scale Operations",
    price: "$99",
    period: "/month",
    tag: null,
    features: [
      "10 Workspaces",
      "Up to 5,000 calls/month",
      "Real-time Order & PO Capture",
      "Custom Voice Tone & Speed",
      "Live Human Handoff Triggers",
      "REST & Webhooks API Access",
      "99.9% Uptime SLA",
    ],
    missing: [],
    cta: "Upgrade to Scale",
    href: "/sign-up?plan=scale",
    popular: false,
  },
  {
    id: "enterprise",
    name: "Enterprise Scale",
    price: "Custom",
    period: "",
    tag: null,
    features: [
      "Unlimited Workspaces & Calls",
      "Custom Voice Cloning & Tone",
      "Dedicated Edge Infrastructure",
      "Custom ERP & CRM Integrations",
      "SOC2 Type II & Audit Logs",
      "24/7 Dedicated Support",
      "Sub-50ms SLA Guarantee",
    ],
    missing: [],
    cta: "Contact Enterprise Team",
    href: "/sign-up?plan=enterprise",
    popular: false,
  },
];

const faqs = [
  { q: "How do the $0, $49, and $99 plans work?", a: "Start completely free with $0 for testing. As your call volume grows, seamlessly upgrade to $49 (Pro) or $99 (Scale) to unlock more capacity and advanced APIs." },
  { q: "Can I change or upgrade my plan anytime?", a: "Yes! You can switch plans or upgrade instantly from your dashboard. Unused call quotas roll over into your new tier." },
  { q: "What happens when I click a plan CTA?", a: "Each plan button takes you directly to the workspace setup form with your selected tier pre-configured and ready to deploy." },
  { q: "What languages and dialects are supported?", a: "VoxFlow supports Hindi, Indian-English, Hinglish, Tamil, Telugu, Marathi, Gujarati, and over 50 global languages natively." },
  { q: "Is caller data and audio secure?", a: "All streams are encrypted in transit (TLS 1.3) and at rest (AES-256). VoxFlow is SOC 2 Type II compliant." },
];

export default function PricingPage() {
  return (
    <div className="pt-[5.5rem] pb-24 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      {/* Header */}
      <FadeUp className="text-center max-w-3xl mx-auto mb-16 pt-12">
        <span className="font-label text-[#00ffcc] uppercase tracking-[0.2em] text-xs mb-4 block">
          ✦ Transparent Pricing
        </span>
        <h1 className="font-headline font-extrabold text-4xl sm:text-6xl tracking-tight text-[#e8e0f0] mb-4 leading-tight">
          Flexible plans for <span className="text-[#ff2d78] neon-text">every team.</span>
        </h1>
        <p className="text-lg text-[#a098b0] font-body">
          Choose between $0 Free Pilot, $49 Pro, $99 Scale, or Custom Enterprise plans. Instant workspace activation.
        </p>
      </FadeUp>

      {/* Pricing Cards — 4 Columns */}
      <StaggerContainer className="max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-24">
        {tiers.map((tier) => (
          <StaggerItem
            key={tier.id}
            className={`relative rounded-2xl border p-6 sm:p-7 flex flex-col transition-all duration-300 ${
              tier.popular
                ? "border-[#ff2d78]/60 bg-[#141422] shadow-[0_0_40px_rgba(255,45,120,0.18)] hover:border-[#ff2d78] scale-[1.02] z-10"
                : "border-[#302840]/40 bg-[#0f0f1a]/80 hover:border-[#ff2d78]/40"
            }`}
          >
            {tier.tag && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 text-[10px] font-label font-bold uppercase tracking-widest bg-[#ff2d78] text-[#1a0010] px-3.5 py-1 rounded-full shadow-[0_0_12px_rgba(255,45,120,0.6)]">
                {tier.tag}
              </span>
            )}
            <h3 className="font-headline font-bold text-xl text-[#e8e0f0] mb-1">{tier.name}</h3>
            <div className="flex items-baseline gap-1 mb-5">
              <span className="font-headline font-black text-4xl sm:text-5xl text-[#e8e0f0]">
                {tier.price}
              </span>
              <span className="text-xs font-label text-[#a098b0]">{tier.period}</span>
            </div>
            <ul className="space-y-3 mb-8 flex-1">
              {tier.features.map((f) => (
                <li key={f} className="flex items-start gap-2.5 text-xs sm:text-sm text-[#e8e0f0]/90 font-body">
                  <Check size={15} className="text-[#00ffcc] mt-0.5 shrink-0" />
                  {f}
                </li>
              ))}
              {tier.missing.map((f) => (
                <li key={f} className="flex items-start gap-2.5 text-xs sm:text-sm text-[#a098b0]/35 font-body line-through">
                  <span className="w-3.5 shrink-0" />
                  {f}
                </li>
              ))}
            </ul>
            <Link
              href={tier.href}
              className={`text-center font-headline font-bold text-xs sm:text-sm px-5 py-3 rounded-xl transition-all duration-200 active:scale-95 ${
                tier.popular
                  ? "bg-[#ff2d78] text-[#1a0010] hover:shadow-[0_0_25px_rgba(255,45,120,0.5)]"
                  : "bg-[#1e1e30] text-[#e8e0f0] hover:bg-[#28283e] border border-[#302840]/60"
              }`}
            >
              {tier.cta}
            </Link>
          </StaggerItem>
        ))}
      </StaggerContainer>

      {/* FAQ */}
      <div className="max-w-4xl mx-auto">
        <FadeUp>
          <h2 className="font-headline font-extrabold text-3xl text-[#e8e0f0] text-center mb-10">
            Frequently Asked Questions
          </h2>
        </FadeUp>
        <StaggerContainer className="space-y-4">
          {faqs.map((faq) => (
            <StaggerItem key={faq.q}>
              <details className="rounded-xl border border-[#302840]/40 bg-[#141422]/70 group">
                <summary className="px-6 py-5 text-base font-headline font-semibold text-[#e8e0f0] cursor-pointer list-none flex items-center justify-between group-open:text-[#ff2d78] transition-colors">
                  {faq.q}
                  <span className="text-[#a098b0] group-open:rotate-180 transition-transform duration-200 text-lg">▾</span>
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
