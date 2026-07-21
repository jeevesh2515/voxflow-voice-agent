import Link from "next/link";
import { ArrowRight, PhoneCall, ShieldCheck, TrendingUp } from "lucide-react";
import { FadeUp, StaggerContainer, StaggerItem } from "@/components/ScrollAnimations";

const values = [
  { icon: PhoneCall, title: "Start small, prove it works", body: "One repeatable workflow, clear outcomes, and a team that remains in control when a situation needs judgment." },
  { icon: ShieldCheck, title: "Built for trust", body: "Every call is recorded, every action is traceable, and every escalation reaches the right person with full context." },
  { icon: TrendingUp, title: "Grow with confidence", body: "Expand only when the outcome earns trust. Add workflows, languages, and integrations at your own pace." },
];

export default function AboutPage() {
  return (
    <div className="pt-[5.5rem] pb-20 px-6">
      <FadeUp className="max-w-4xl mx-auto text-center mb-16 pt-12">
        <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-primary">About VoxFlow Voice Agent</span>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-foreground mt-4 mb-6">
          Voice operations, automated for the work behind every call.
        </h1>
        <p className="text-lg text-muted-foreground leading-7 max-w-3xl mx-auto">
          VoxFlow Voice Agent gives business teams a clear, reliable way to handle high-volume phone workflows.
          The initial pilot handles Hindi-English supplier conversations, captures POs and orders, checks stock,
          shares shipment updates, and records every call.
        </p>
      </FadeUp>

      <FadeUp delay={0.1} className="max-w-5xl mx-auto mb-20">
        <div className="rounded-[1.25rem] border border-border bg-card p-8 sm:p-12">
          <p className="text-base sm:text-lg text-foreground/80 leading-7 mb-10">
            We believe useful automation starts small: one repeatable workflow, clear outcomes, and a team
            that remains in control when a situation needs judgment. That is how VoxFlow Voice Agent grows
            with your operations.
          </p>
          <StaggerContainer className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {values.map((v) => (
              <StaggerItem key={v.title} className="text-center">
                <div className="h-10 w-10 rounded-lg bg-primary/10 grid place-items-center mx-auto mb-3">
                  <v.icon className="text-primary" size={20} />
                </div>
                <h3 className="text-sm font-semibold text-foreground mb-2">{v.title}</h3>
                <p className="text-sm text-muted-foreground leading-6">{v.body}</p>
              </StaggerItem>
            ))}
          </StaggerContainer>
        </div>
      </FadeUp>

      <FadeUp className="text-center">
        <h2 className="text-2xl font-bold text-foreground mb-4">Ready to make every call more useful?</h2>
        <p className="text-muted-foreground mb-8">Start with one call flow and build from there with VoxFlow Voice Agent.</p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            href="/sign-up"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-all duration-200 group"
          >
            Build a call flow <ArrowRight size={14} className="transition-transform duration-200 group-hover:translate-x-1" />
          </Link>
          <Link
            href="/pricing"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-border bg-accent text-foreground text-sm font-medium hover:bg-accent/80 transition-all duration-200"
          >
            See pricing
          </Link>
        </div>
      </FadeUp>
    </div>
  );
}
