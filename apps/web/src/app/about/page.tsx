import Link from "next/link";
import { ArrowRight, PhoneCall, ShieldCheck, TrendingUp, Cpu, Globe, Zap } from "lucide-react";
import { FadeUp, StaggerContainer, StaggerItem } from "@/components/ScrollAnimations";

const values = [
  { icon: PhoneCall, title: "Precision Automation", body: "Handle complex Hindi-English & multilingual calls with zero latency and perfect protocol adherence." },
  { icon: ShieldCheck, title: "Enterprise Reliability", body: "SOC2 Type II certified security. Every conversation logged, transcribed, and audited with full context." },
  { icon: TrendingUp, title: "Operational Growth", body: "Scale from 50 to 5,000+ daily calls seamlessly without expanding call center headcount." },
  { icon: Cpu, title: "Autonomous Intelligence", body: "Integrates directly into ERP, CRM, and inventory databases for real-time order & shipment lookups." },
  { icon: Globe, title: "50+ Global Languages", body: "Native fluency in regional dialects, switching context dynamically to suit the customer." },
  { icon: Zap, title: "Instant Response", body: "Under 50ms voice latency ensures natural conversational flow with zero lag or interruption." },
];

export default function AboutPage() {
  return (
    <div className="pt-[5.5rem] pb-24 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      {/* Hero */}
      <FadeUp className="max-w-4xl mx-auto text-center mb-16 pt-12">
        <span className="font-label text-[#00ffcc] uppercase tracking-[0.2em] text-xs mb-4 block text-shadow-sm">
          ✦ About VoxFlow Voice Agent
        </span>
        <h1 className="font-headline font-extrabold text-4xl sm:text-6xl tracking-tight text-[#e8e0f0] mb-6 leading-tight">
          The voice layer for <span className="text-[#ff2d78] neon-text">modern operations.</span>
        </h1>
        <p className="text-lg sm:text-xl text-[#a098b0] leading-relaxed max-w-3xl mx-auto font-body">
          VoxFlow provides enterprise operational teams with an autonomous, high-precision voice intelligence engine. Built for scale, trusted by industry leaders to automate high-stakes supplier and customer calls.
        </p>
      </FadeUp>

      {/* Main Philosophy Card */}
      <FadeUp delay={0.1} className="mb-20">
        <div className="rounded-2xl border border-[#ff2d78]/20 bg-[#0f0f1a]/60 backdrop-blur-xl p-8 sm:p-12 shadow-[0_0_40px_rgba(255,45,120,0.08)]">
          <p className="text-lg sm:text-xl text-[#e8e0f0] font-headline font-semibold leading-relaxed mb-10 text-center max-w-4xl mx-auto">
            &ldquo;Useful voice automation starts with surgical clarity: handling high-frequency operational calls with zero margin for error while giving humans instant auditability.&rdquo;
          </p>
          <StaggerContainer className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {values.map((v) => (
              <StaggerItem key={v.title} className="rounded-xl border border-[#302840]/40 bg-[#141422]/80 p-6 hover:border-[#ff2d78]/40 transition-all duration-300 group">
                <div className="h-12 w-12 rounded-xl bg-[#ff2d78]/10 border border-[#ff2d78]/30 grid place-items-center mb-4 group-hover:scale-110 transition-transform">
                  <v.icon className="text-[#ff2d78]" size={22} />
                </div>
                <h3 className="font-headline font-bold text-lg text-[#e8e0f0] mb-2">{v.title}</h3>
                <p className="text-sm text-[#a098b0] font-body leading-relaxed">{v.body}</p>
              </StaggerItem>
            ))}
          </StaggerContainer>
        </div>
      </FadeUp>

      {/* Call to Action */}
      <FadeUp className="text-center bg-[#141422]/50 border border-[#302840]/40 rounded-3xl p-10 sm:p-14 relative overflow-hidden">
        <h2 className="font-headline font-extrabold text-3xl sm:text-4xl text-[#e8e0f0] mb-4">
          Ready to automate your <span className="text-[#ff2d78]">voice layer</span>?
        </h2>
        <p className="text-[#a098b0] text-base sm:text-lg mb-8 max-w-2xl mx-auto font-body">
          Deploy pre-configured voice flows for inventory check, purchase order logging, and customer inquiry handling in minutes.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="/sign-up"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-xl bg-[#ff2d78] text-[#1a0010] font-headline font-bold text-base hover:shadow-[0_0_25px_rgba(255,45,120,0.5)] transition-all duration-200 group active:scale-95"
          >
            Deploy Voice Agent <ArrowRight size={18} className="transition-transform duration-200 group-hover:translate-x-1" />
          </Link>
          <Link
            href="/pricing"
            className="inline-flex items-center gap-2 px-8 py-4 rounded-xl border border-[#302840]/60 bg-[#1e1e30] text-[#e8e0f0] font-headline font-bold text-base hover:bg-[#28283e] transition-all duration-200 active:scale-95"
          >
            View Pricing &amp; Plans
          </Link>
        </div>
      </FadeUp>
    </div>
  );
}
