"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { FadeUp } from "@/components/ScrollAnimations";

const planNames: Record<string, { label: string; price: string }> = {
  starter: { label: "Starter Pilot", price: "$0/mo" },
  pro: { label: "Pro Operations", price: "$49/mo" },
  scale: { label: "Scale Operations", price: "$99/mo" },
  enterprise: { label: "Enterprise Scale", price: "Custom" },
};

function SignUpContent() {
  const searchParams = useSearchParams();
  const planKey = searchParams.get("plan") || "pro";
  const [selectedPlan, setSelectedPlan] = useState(planKey);
  const activePlan = planNames[selectedPlan] || planNames.pro;

  return (
    <FadeUp className="w-full max-w-lg relative z-10">
      <div className="glass neon-border rounded-2xl p-8 sm:p-10 border border-[#ff2d78]/30 shadow-[0_0_50px_rgba(0,0,0,0.5)]">
        <div className="text-center mb-8">
          <div className="h-12 w-12 rounded-xl bg-[#ff2d78] grid place-items-center font-headline font-extrabold text-[#1a0010] text-xl mx-auto mb-4 shadow-[0_0_20px_rgba(255,45,120,0.5)]">
            V
          </div>
          <h1 className="font-headline font-bold text-2xl sm:text-3xl text-[#e8e0f0]">
            Activate Your Workspace
          </h1>
          <p className="text-sm text-[#a098b0] mt-2 font-body">
            Deploy VoxFlow voice operations for your team
          </p>

          {/* Selected Plan Badge */}
          <div className="mt-4 inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#ff2d78]/15 border border-[#ff2d78]/40 text-xs font-label text-[#ff2d78]">
            <span className="w-2 h-2 rounded-full bg-[#00ffcc] animate-pulse" />
            Selected Plan: <strong className="text-[#e8e0f0]">{activePlan.label} ({activePlan.price})</strong>
          </div>
        </div>

        <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
          {/* Plan Selector Radios */}
          <div>
            <label className="text-xs font-label uppercase tracking-widest text-[#e8e0f0] block mb-2">
              Select Plan Tier
            </label>
            <div className="grid grid-cols-2 gap-2 mb-2">
              {[
                { key: "starter", name: "Starter ($0)", sub: "Free Pilot" },
                { key: "pro", name: "Pro ($49)", sub: "1.5k calls" },
                { key: "scale", name: "Scale ($99)", sub: "5k calls" },
                { key: "enterprise", name: "Enterprise", sub: "Custom" },
              ].map((p) => (
                <button
                  key={p.key}
                  type="button"
                  onClick={() => setSelectedPlan(p.key)}
                  className={`p-2.5 rounded-xl border text-left transition-all ${
                    selectedPlan === p.key
                      ? "border-[#ff2d78] bg-[#ff2d78]/10 text-[#e8e0f0]"
                      : "border-[#302840]/60 bg-[#141422] text-[#a098b0] hover:border-[#ff2d78]/40"
                  }`}
                >
                  <div className="text-xs font-headline font-bold">{p.name}</div>
                  <div className="text-[10px] text-[#a098b0]">{p.sub}</div>
                </button>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="name" className="text-xs font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
              Full Name
            </label>
            <input
              id="name"
              type="text"
              placeholder="Sarah Chen"
              className="w-full px-4 py-3 rounded-xl bg-[#141422] border border-[#302840]/60 text-[#e8e0f0] text-sm placeholder:text-[#a098b0]/40 focus:outline-none focus:border-[#ff2d78] focus:ring-1 focus:ring-[#ff2d78]/40 transition-all font-body"
            />
          </div>

          <div>
            <label htmlFor="email" className="text-xs font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
              Work Email
            </label>
            <input
              id="email"
              type="email"
              placeholder="sarah@company.com"
              className="w-full px-4 py-3 rounded-xl bg-[#141422] border border-[#302840]/60 text-[#e8e0f0] text-sm placeholder:text-[#a098b0]/40 focus:outline-none focus:border-[#ff2d78] focus:ring-1 focus:ring-[#ff2d78]/40 transition-all font-body"
            />
          </div>

          <div>
            <label htmlFor="company" className="text-xs font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
              Company / Operation Name
            </label>
            <input
              id="company"
              type="text"
              placeholder="ZenithTech Logistics"
              className="w-full px-4 py-3 rounded-xl bg-[#141422] border border-[#302840]/60 text-[#e8e0f0] text-sm placeholder:text-[#a098b0]/40 focus:outline-none focus:border-[#ff2d78] focus:ring-1 focus:ring-[#ff2d78]/40 transition-all font-body"
            />
          </div>

          <button
            type="submit"
            className="w-full py-3.5 rounded-xl bg-[#ff2d78] text-[#1a0010] font-headline font-bold text-sm hover:shadow-[0_0_25px_rgba(255,45,120,0.5)] transition-all duration-200 active:scale-95 mt-2"
          >
            Deploy {activePlan.label} ({activePlan.price})
          </button>
        </form>

        <p className="text-center text-xs font-label text-[#a098b0] mt-8">
          Already have a workspace?{" "}
          <Link href="/sign-in" className="text-[#00ffcc] hover:text-[#00ffcc]/80 transition-colors font-bold">
            Sign In
          </Link>
        </p>
      </div>
    </FadeUp>
  );
}

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 sm:px-6 pt-[5.5rem] pb-20 bg-[#0a0a12] grid-bg relative overflow-hidden">
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-96 h-96 bg-[#00ffcc]/10 blur-[120px] rounded-full pointer-events-none" />
      <Suspense fallback={<div className="text-center text-[#a098b0] font-label">Loading setup...</div>}>
        <SignUpContent />
      </Suspense>
    </div>
  );
}
