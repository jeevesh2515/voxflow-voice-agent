"use client";

import Link from "next/link";
import { faq } from "@/data/faq";

export default function FaqAndContact() {
  return (
    <div className="w-full max-w-6xl mx-auto">
      {/* Section Header */}
      <div className="text-center mb-14">
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full border border-white/[0.08] bg-white/[0.02] text-xs font-mono tracking-widest text-[#5EEAD4] uppercase mb-4">
          <span className="h-1.5 w-1.5 rounded-full bg-[#5EEAD4] animate-pulse" />
          08 / 08 • Support & Conversion // FAQ & Same-Day Operations Contact
        </div>
        <h2 className="font-headline font-black text-3xl sm:text-5xl lg:text-6xl tracking-tight text-white leading-[1.08]">
          Everything you need <br />
          <span className="text-white/60">to deploy and go live.</span>
        </h2>
        <p className="font-sans text-base sm:text-lg text-white/70 max-w-2xl mx-auto mt-4 leading-relaxed">
          Common operational questions answered. Or reach our engineering team directly for same-day setup.
        </p>
      </div>

      {/* FAQ Accordion (Directly consuming src/data/faq.ts) */}
      <div className="space-y-3.5 mb-16 max-w-4xl mx-auto">
        {faq.map((item, idx) => (
          <details
            key={idx}
            className="group rounded-2xl border border-white/[0.08] bg-[#030308]/90 backdrop-blur-xl transition-all duration-200 open:border-[#5EEAD4]/40 open:bg-[#030308]/95"
          >
            <summary className="flex items-center justify-between p-5 sm:p-6 cursor-pointer list-none select-none font-headline font-bold text-sm sm:text-base text-white group-open:text-[#5EEAD4] transition-colors">
              <span className="flex items-center gap-3">
                <span className="font-mono text-xs text-white/40 group-open:text-[#5EEAD4]">
                  {String(idx + 1).padStart(2, "0")}
                </span>
                <span>{item.q}</span>
              </span>
              <span className="ml-4 font-mono text-xs text-white/40 group-open:rotate-180 group-open:text-[#5EEAD4] transition-transform duration-200">
                ▾
              </span>
            </summary>
            <div className="px-5 sm:px-6 pb-6 pt-1 text-xs sm:text-sm text-white/70 font-sans leading-relaxed border-t border-white/[0.04]">
              {item.a}
            </div>
          </details>
        ))}
      </div>

      {/* Same-Day Operations Contact & Final Conversion Block */}
      <div className="rounded-3xl border border-[#5EEAD4]/30 bg-gradient-to-b from-[#5EEAD4]/[0.08] to-transparent backdrop-blur-2xl p-8 sm:p-12 shadow-[0_0_50px_rgba(94,234,212,0.1)] relative overflow-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          <div className="lg:col-span-7 space-y-4">
            <div className="inline-flex items-center gap-2 font-mono text-xs text-[#5EEAD4] uppercase tracking-wider">
              <span className="h-2 w-2 rounded-full bg-[#5EEAD4] animate-ping" />
              Same-Day Depot Deployment Available
            </div>
            <h3 className="font-headline font-black text-2xl sm:text-4xl text-white tracking-tight leading-tight">
              Fix one freight workflow this week.
            </h3>
            <p className="font-sans text-sm sm:text-base text-white/70 leading-relaxed max-w-xl">
              Start with 500 free minutes on a 14-day trial, or speak directly with our solutions engineering team to connect an existing UK DID number today.
            </p>

            <div className="pt-4 flex flex-wrap items-center gap-6 font-mono text-xs text-white/60">
              <div>
                <span className="block text-[10px] text-white/40 uppercase">Direct Phone</span>
                <span className="text-white font-bold">+44 20 7946 0991</span>
              </div>
              <div>
                <span className="block text-[10px] text-white/40 uppercase">Operations Email</span>
                <a href="mailto:operations@voxflow.ai" className="text-[#5EEAD4] hover:underline">
                  operations@voxflow.ai
                </a>
              </div>
              <div>
                <span className="block text-[10px] text-white/40 uppercase">SLA Target</span>
                <span className="text-emerald-400 font-bold">&lt; 2h Response</span>
              </div>
            </div>
          </div>

          <div className="lg:col-span-5 flex flex-col sm:flex-row lg:flex-col gap-3 justify-center">
            <Link
              href="/sign-up"
              className="inline-flex items-center justify-center rounded-xl bg-[#5EEAD4] px-6 py-3.5 font-headline font-black text-sm text-[#030308] hover:shadow-[0_0_25px_rgba(94,234,212,0.4)] transition active:scale-95 text-center"
            >
              Start Free Trial (500 Mins) →
            </Link>
            <a
              href="mailto:operations@voxflow.ai?subject=Operations%20Review%20Request"
              className="inline-flex items-center justify-center rounded-xl border border-white/[0.12] bg-white/[0.04] px-6 py-3.5 font-headline font-bold text-sm text-white hover:bg-white/[0.08] hover:border-white/[0.2] transition text-center"
            >
              Book an Operations Review
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
