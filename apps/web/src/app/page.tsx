import Link from "next/link";
import { ArrowRight, Headphones, ScrollText, ShieldCheck, PhoneCall, Database, Workflow, ClipboardCheck, Check } from "lucide-react";
import { FadeUp, FadeIn, StaggerContainer, StaggerItem, ScaleIn } from "@/components/ScrollAnimations";

const ConsoleMockup = () => (
  <div className="relative">
    <div className="vox-console-glow rounded-[1.25rem] border border-border bg-card overflow-hidden">
      <div className="flex items-center gap-1.5 px-4 py-3 border-b border-border">
        <span className="h-2.5 w-2.5 rounded-full bg-danger-500" />
        <span className="h-2.5 w-2.5 rounded-full bg-warn-500" />
        <span className="h-2.5 w-2.5 rounded-full bg-success-500" />
        <span className="ml-3 text-[10px] font-mono uppercase tracking-[0.12em] text-muted-foreground">Live operations</span>
        <span className="ml-auto text-[9px] font-mono uppercase tracking-[0.12em] text-success-500 bg-success-500/10 rounded-sm px-2 py-0.5 border border-success-500/20">System active</span>
      </div>

      <div className="grid grid-cols-[92px_1fr] sm:grid-cols-[138px_1fr] min-h-[320px]">
        <div className="border-r border-border p-3 space-y-1">
          {["VoxFlow", "Overview", "Calls", "Orders", "Workflows", "Analytics"].map((item, i) => (
            <div
              key={item}
              className={`text-[10px] font-mono uppercase tracking-[0.08em] px-2 py-1.5 rounded-md ${
                i === 1 ? "bg-primary/10 text-primary font-medium" : "text-muted-foreground"
              }`}
            >
              {item}
            </div>
          ))}
        </div>

        <div className="p-4 sm:p-5">
          <div className="flex items-center gap-2 mb-4">
            <span className="h-2 w-2 rounded-full bg-success-500 pulse-dot" />
            <span className="text-xs font-mono uppercase tracking-[0.12em] text-muted-foreground">Live operations</span>
            <span className="text-[10px] text-muted-foreground ml-auto">All systems active</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
            {[
              { label: "Live calls", value: "12", sub: "Across supplier operations" },
              { label: "Orders completed", value: "223", sub: "+24% today" },
              { label: "Average handoff", value: "01:18", sub: "Escalations only" },
            ].map((s) => (
              <div key={s.label} className="rounded-lg border border-border bg-card/70 p-3 sm:p-4">
                <div className="text-[10px] font-mono uppercase tracking-[0.12em] text-muted-foreground mb-1">{s.label}</div>
                <div className="text-2xl sm:text-3xl font-medium text-foreground tracking-tight">{s.value}</div>
                <div className="text-xs text-muted-foreground mt-0.5">{s.sub}</div>
              </div>
            ))}
          </div>

          <div className="rounded-lg border border-primary/30 bg-primary/5 p-3 sm:p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="h-1.5 w-1.5 rounded-full bg-primary pulse-ring" />
              <span className="text-[10px] font-mono uppercase tracking-[0.12em] text-primary">Active call</span>
              <span className="text-xs text-muted-foreground ml-auto">GURGAON, IN</span>
            </div>
            <div className="text-sm font-semibold text-foreground">Shree Traders</div>
            <div className="text-xs text-muted-foreground">PO verification &middot; 02:14</div>
            <div className="mt-3 flex items-center gap-3">
              <div className="vox-wave">
                {Array.from({ length: 12 }).map((_, i) => (
                  <span key={i} />
                ))}
              </div>
              <span className="text-[11px] font-mono text-primary/80 italic">&gt; listening for order details</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
);

export default function Home() {
  return (
    <>
      {/* ==================== HERO ==================== */}
      <section className="relative min-h-screen flex items-center overflow-hidden border-b border-border">
        <div className="absolute inset-0 vox-grid vox-radial" />
        <div className="absolute bottom-0 vox-signal" />
        <div className="absolute top-1/3 left-1/4 w-[600px] h-[600px] bg-primary/5 rounded-full blur-[120px]" />

        <div className="relative z-10 mx-auto max-w-7xl w-full px-4 sm:px-6 lg:px-8 pt-24 pb-16 sm:pb-20">
          <div className="lg:grid lg:grid-cols-[0.9fr_1.1fr] lg:gap-12 items-center">
            {/* Left: Text */}
            <div className="max-w-xl">
              <FadeUp>
                <div className="inline-flex items-center gap-2 rounded-sm border border-primary/30 bg-primary/10 px-2 py-1 font-mono text-[9px] uppercase tracking-[0.12em] text-primary mb-6">
                  <span className="h-1.5 w-1.5 rounded-full bg-success-500 pulse-dot" />
                  Voice operations, automated
                </div>
              </FadeUp>

              <FadeUp delay={0.1}>
                <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-[-0.055em] leading-[1.03] text-foreground text-balance">
                  Every call. Every detail.{" "}
                  <span className="text-primary">Handled.</span>
                </h1>
              </FadeUp>

              <FadeUp delay={0.2}>
                <p className="mt-6 text-base sm:text-lg text-muted-foreground leading-7 sm:leading-8 max-w-lg">
                  VoxFlow Voice Agent resolves supplier calls with the context, controls, and operational memory your business needs to move with confidence.
                </p>
              </FadeUp>

              <FadeUp delay={0.3}>
                <div className="mt-8 flex flex-col sm:flex-row items-start gap-3">
                  <Link
                    href="/sign-up"
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-all duration-200 group"
                  >
                    Request an operations pilot
                    <ArrowRight size={14} className="transition-transform duration-200 group-hover:translate-x-1" />
                  </Link>
                  <Link
                    href="#operations"
                    className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-border bg-accent text-foreground text-sm font-medium hover:bg-accent/80 transition-all duration-200"
                  >
                    Explore call operations
                  </Link>
                </div>
              </FadeUp>

              <FadeUp delay={0.35}>
                <div className="mt-6 text-xs text-muted-foreground font-mono tracking-[0.08em]">
                  Hindi + English &middot; controlled rollout
                </div>
              </FadeUp>
            </div>

            {/* Right: Console */}
            <div className="mt-12 lg:mt-0">
              <ScaleIn delay={0.2}>
                <ConsoleMockup />
              </ScaleIn>
            </div>
          </div>
        </div>
      </section>

      {/* ==================== BUILT FOR THE DETAILS ==================== */}
      <section className="py-16 sm:py-20 border-b border-border bg-card/35">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="sm:grid sm:grid-cols-[0.9fr_2.1fr] sm:gap-12 lg:gap-20 items-start">
            <FadeUp>
              <h2 className="text-xl sm:text-2xl font-semibold tracking-tight text-foreground mb-4 sm:mb-0">
                Built for the details that <span className="text-primary">cannot be lost</span>
              </h2>
            </FadeUp>
            <StaggerContainer className="grid grid-cols-1 sm:grid-cols-3 gap-6">
              <StaggerItem>
                <div className="flex flex-col gap-2">
                  <Headphones className="text-primary" size={20} />
                  <h3 className="text-lg font-semibold text-foreground tracking-tight">Calls stay consistent</h3>
                  <p className="text-sm text-muted-foreground leading-6">Approved answers, across every shift.</p>
                </div>
              </StaggerItem>
              <StaggerItem>
                <div className="flex flex-col gap-2">
                  <ScrollText className="text-primary" size={20} />
                  <h3 className="text-lg font-semibold text-foreground tracking-tight">Records stay complete</h3>
                  <p className="text-sm text-muted-foreground leading-6">Every call creates useful operational context.</p>
                </div>
              </StaggerItem>
              <StaggerItem>
                <div className="flex flex-col gap-2">
                  <ShieldCheck className="text-primary" size={20} />
                  <h3 className="text-lg font-semibold text-foreground tracking-tight">Teams stay in control</h3>
                  <p className="text-sm text-muted-foreground leading-6">Exceptions reach the right human, fast.</p>
                </div>
              </StaggerItem>
            </StaggerContainer>
          </div>
        </div>
      </section>

      {/* ==================== OPERATIONS ==================== */}
      <section id="operations" className="py-16 sm:py-24 lg:py-28 border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="lg:grid lg:grid-cols-[0.85fr_1.15fr] lg:gap-16 items-start">
            <FadeUp>
              <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-primary">Voice, flow, control</span>
              <h2 className="mt-4 text-3xl sm:text-4xl lg:text-4xl font-semibold tracking-[-0.045em] leading-[1.1] text-foreground text-balance">
                The call is only the beginning of the operation.
              </h2>
              <p className="mt-5 text-sm sm:text-base text-muted-foreground leading-6 max-w-md">
                VoxFlow is designed around the work that starts when a supplier picks up the phone&mdash;data checks, confirmations, actions, and traceable outcomes.
              </p>
              <div className="mt-8">
                <Link
                  href="/pricing"
                  className="inline-flex items-center gap-2 text-sm font-medium text-primary hover:text-primary/80 transition-colors duration-200 group"
                >
                  View pilot options
                  <ArrowRight size={14} className="transition-transform duration-200 group-hover:translate-x-1" />
                </Link>
              </div>
            </FadeUp>

            <StaggerContainer className="mt-10 lg:mt-0 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <StaggerItem className="sm:col-span-2">
                <div className="rounded-[1.25rem] border border-border bg-primary/10 p-6 sm:p-7">
                  <div className="flex items-start gap-4">
                    <PhoneCall className="text-primary shrink-0 mt-0.5" size={20} />
                    <div>
                      <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-primary">Supplier line</span>
                      <h3 className="mt-2 text-base sm:text-lg font-semibold text-foreground tracking-tight">Capture orders and POs without leaving ambiguity in the call.</h3>
                      <p className="mt-2 text-sm text-muted-foreground leading-6">The agent listens, confirms critical details, and creates a searchable operational record your team can trust.</p>
                    </div>
                  </div>
                </div>
              </StaggerItem>
              <StaggerItem>
                <div className="rounded-[1.25rem] border border-border bg-card p-6 sm:p-7">
                  <Database className="text-primary" size={20} />
                  <span className="mt-4 block font-mono text-[10px] uppercase tracking-[0.15em] text-primary">Information line</span>
                  <h3 className="mt-2 text-base font-semibold text-foreground tracking-tight">Answer stock and shipment questions from approved data.</h3>
                  <p className="mt-2 text-sm text-muted-foreground leading-6">Give suppliers timely, consistent status without asking a team member to chase it down.</p>
                </div>
              </StaggerItem>
              <StaggerItem>
                <div className="rounded-[1.25rem] border border-border bg-card p-6 sm:p-7">
                  <Workflow className="text-primary" size={20} />
                  <span className="mt-4 block font-mono text-[10px] uppercase tracking-[0.15em] text-primary">Exception line</span>
                  <h3 className="mt-2 text-base font-semibold text-foreground tracking-tight">Route the calls that need a human decision.</h3>
                  <p className="mt-2 text-sm text-muted-foreground leading-6">Escalation is part of the workflow, so priority calls never disappear into an inbox.</p>
                </div>
              </StaggerItem>
            </StaggerContainer>
          </div>
        </div>
      </section>

      {/* ==================== HOW IT WORKS ==================== */}
      <section id="how-it-works" className="py-16 sm:py-24 lg:py-28 border-y border-border bg-panel">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <FadeUp className="text-center max-w-2xl mx-auto mb-14 sm:mb-16">
            <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-primary">From ring to record</span>
            <h2 className="mt-4 text-3xl sm:text-4xl lg:text-4xl font-semibold tracking-[-0.045em] leading-[1.1] text-foreground">
              A composed call flow for high-accountability teams.
            </h2>
          </FadeUp>

          <StaggerContainer className="grid grid-cols-1 md:grid-cols-3 border border-border rounded-[1.25rem] overflow-hidden bg-card">
            {[
              { num: "01", title: "Listen with context", body: "The agent recognizes the caller, intent, language, and workflow before it responds." },
              { num: "02", title: "Verify against your systems", body: "Approved stock, PO, and shipment information is checked in real time\u2014not improvised." },
              { num: "03", title: "Complete the operational loop", body: "VoxFlow records every request, confirmation, and exception for the people who own the outcome." },
            ].map((step, i) => (
              <StaggerItem key={step.num} className={`p-6 sm:p-8 lg:p-10 ${i < 2 ? "border-b md:border-b-0 md:border-r border-border" : ""}`}>
                <span className="text-5xl sm:text-6xl font-bold text-primary/15 leading-none">{step.num}</span>
                <h3 className="mt-4 text-lg sm:text-xl font-semibold text-foreground tracking-tight">{step.title}</h3>
                <p className="mt-3 text-sm text-muted-foreground leading-6">{step.body}</p>
                <div className="mt-6 text-muted-foreground">
                  <ArrowRight size={16} className="text-primary/40" />
                </div>
              </StaggerItem>
            ))}
          </StaggerContainer>
        </div>
      </section>

      {/* ==================== OPERATIONAL TRUST ==================== */}
      <section className="py-16 sm:py-24 lg:py-28">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="lg:grid lg:grid-cols-[0.85fr_1.15fr] lg:gap-12 rounded-[1.25rem] border border-border bg-card p-6 sm:p-10">
            <FadeUp>
              <div className="h-10 w-10 rounded-lg bg-primary/10 grid place-items-center mb-4">
                <ShieldCheck className="text-primary" size={20} />
              </div>
              <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-primary">Operational trust</span>
              <h2 className="mt-4 text-2xl sm:text-3xl font-semibold tracking-tight leading-[1.1] text-foreground">
                Enterprise context without a black-box handoff.
              </h2>
              <p className="mt-4 text-sm text-muted-foreground leading-6 max-w-sm">
                VoxFlow is built to keep the decision trail visible: what the caller asked, what information was given, and where a human stepped in.
              </p>
            </FadeUp>

            <StaggerContainer className="mt-8 lg:mt-0 grid grid-cols-1 sm:grid-cols-2 gap-px bg-border rounded-xl overflow-hidden">
              {[
                { icon: ClipboardCheck, title: "Structured transcripts", body: "Searchable call details instead of scattered notes." },
                { icon: Headphones, title: "Intentional handoffs", body: "Exceptions route to people with the right context." },
                { icon: Database, title: "Approved information", body: "Responses come from the data you choose to expose." },
                { icon: Check, title: "Controlled rollout", body: "Prove one workflow before expanding the system." },
              ].map((item) => (
                <StaggerItem key={item.title} className="bg-card p-5 sm:p-6">
                  <item.icon className="text-primary" size={20} />
                  <h3 className="mt-3 text-sm font-semibold text-foreground">{item.title}</h3>
                  <p className="mt-1.5 text-xs text-muted-foreground leading-5">{item.body}</p>
                </StaggerItem>
              ))}
            </StaggerContainer>
          </div>
        </div>
      </section>

      {/* ==================== CTA ==================== */}
      <section className="py-16 sm:py-24 border-t border-border bg-panel relative overflow-hidden">
        <div className="absolute inset-0 vox-grid opacity-50" />
        <div className="relative z-10 mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 text-center">
          <FadeUp>
            <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-primary">VoxFlow operations pilot</span>
            <h2 className="mt-4 text-3xl sm:text-4xl lg:text-5xl font-semibold tracking-[-0.05em] leading-[1.08] text-foreground text-balance">
              Put your highest-volume calls on a better path.
            </h2>
            <p className="mt-5 text-sm sm:text-base text-muted-foreground leading-6 max-w-xl mx-auto">
              Begin with a focused supplier workflow. See exactly how calls are handled. Expand only after the outcome earns trust.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link
                href="/sign-up"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-all duration-200 group"
              >
                Request an operations pilot
                <ArrowRight size={14} className="transition-transform duration-200 group-hover:translate-x-1" />
              </Link>
              <Link
                href="/pricing"
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-border bg-accent text-foreground text-sm font-medium hover:bg-accent/80 transition-all duration-200"
              >
                Review pilot options
              </Link>
            </div>
          </FadeUp>
        </div>
      </section>
    </>
  );
}
