import Link from "next/link";
import { Check } from "lucide-react";
import { FadeUp, StaggerContainer, StaggerItem } from "@/components/ScrollAnimations";

const tiers = [
  {
    name: "Free", price: "$0", period: "/month", tag: null,
    features: ["1 workspace", "Up to 3 team members", "Basic analytics", "Community support"],
    missing: ["Custom branding", "Priority support", "SSO & SAML", "SLA guarantee"],
    cta: "Get Started", href: "/sign-up", popular: false,
  },
  {
    name: "Pro", price: "$29", period: "/month", tag: "Most Popular",
    features: ["Unlimited workspaces", "Up to 20 team members", "Advanced analytics", "Priority support", "Custom branding", "API access"],
    missing: [],
    cta: "Start Free Trial", href: "/sign-up", popular: true,
  },
  {
    name: "Enterprise", price: "$99", period: "/month", tag: null,
    features: ["Everything in Pro", "Unlimited team members", "Advanced analytics", "Dedicated support", "Custom branding", "API access", "SSO & SAML", "SLA guarantee"],
    missing: [],
    cta: "Contact Sales", href: "/sign-up", popular: false,
  },
];

const faqs = [
  { q: "Can I try before I buy?", a: "Yes, start with our Free plan or a 14-day Pro trial. No credit card required." },
  { q: "What happens when my trial ends?", a: "Your data stays. You can downgrade to Free or upgrade to Pro. Nothing is lost." },
  { q: "Can I change plans at any time?", a: "Yes. Upgrade or downgrade instantly. Changes take effect on your next billing cycle." },
  { q: "Do you offer annual billing?", a: "Yes. Annual plans come with a 20% discount compared to monthly billing." },
  { q: "What payment methods do you accept?", a: "We accept all major credit cards, debit cards, and UPI." },
];

export default function PricingPage() {
  return (
    <div className="pt-[5.5rem] pb-20">
      <FadeUp className="text-center max-w-3xl mx-auto mb-16 px-6 pt-12">
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-foreground mb-4">Pricing</h1>
        <p className="text-lg text-muted-foreground">Choose the plan that fits your needs. Start free, upgrade when you&apos;re ready.</p>
      </FadeUp>

      <StaggerContainer className="max-w-6xl mx-auto px-6 grid grid-cols-1 md:grid-cols-3 gap-6 mb-24">
        {tiers.map((tier) => (
          <StaggerItem
            key={tier.name}
            className={`relative rounded-[1.25rem] border p-8 flex flex-col ${
              tier.popular
                ? "border-primary/50 bg-primary/5 shadow-xl shadow-primary/5"
                : "border-border bg-card"
            }`}
          >
            {tier.tag && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 text-[10px] font-mono uppercase tracking-[0.12em] bg-primary text-primary-foreground px-3 py-1 rounded-full">
                {tier.tag}
              </span>
            )}
            <h3 className="text-lg font-semibold text-foreground mb-1">{tier.name}</h3>
            <div className="flex items-baseline gap-1 mb-6">
              <span className="text-4xl font-bold text-foreground">{tier.price}</span>
              <span className="text-sm text-muted-foreground">{tier.period}</span>
            </div>
            <ul className="space-y-3 mb-8 flex-1">
              {tier.features.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-foreground/80">
                  <Check size={16} className="text-success-500 mt-0.5 shrink-0" />
                  {f}
                </li>
              ))}
              {tier.missing.map((f) => (
                <li key={f} className="flex items-start gap-2 text-sm text-muted-foreground">
                  <span className="w-4 shrink-0" />
                  {f}
                </li>
              ))}
            </ul>
            <Link
              href={tier.href}
              className={`text-center text-sm font-medium px-5 py-2.5 rounded-lg transition-all duration-200 ${
                tier.popular
                  ? "bg-primary text-primary-foreground hover:bg-primary/90"
                  : "bg-accent text-foreground hover:bg-accent/80 border border-border"
              }`}
            >
              {tier.cta}
            </Link>
          </StaggerItem>
        ))}
      </StaggerContainer>

      <div className="max-w-3xl mx-auto px-6">
        <FadeUp>
          <h2 className="text-2xl font-bold text-foreground text-center mb-10">Pricing FAQ</h2>
        </FadeUp>
        <StaggerContainer className="space-y-3">
          {faqs.map((faq) => (
            <StaggerItem key={faq.q}>
              <details className="rounded-xl border border-border bg-card group">
                <summary className="px-6 py-4 text-sm font-medium text-foreground/80 cursor-pointer list-none flex items-center justify-between group-open:text-primary transition-colors">
                  {faq.q}
                  <span className="text-muted-foreground group-open:rotate-180 transition-transform duration-200 text-lg">▾</span>
                </summary>
                <div className="px-6 pb-4 text-sm text-muted-foreground leading-6">{faq.a}</div>
              </details>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </div>
    </div>
  );
}
