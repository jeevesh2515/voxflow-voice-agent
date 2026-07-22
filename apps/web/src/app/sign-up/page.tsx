"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { FadeUp } from "@/components/ScrollAnimations";
import { useTenant } from "@/lib/tenant-context";

const planNames: Record<string, { label: string; price: string }> = {
  starter: { label: "Starter Pilot", price: "$0/mo" },
  pro: { label: "Pro Operations", price: "$49/mo" },
  scale: { label: "Scale Operations", price: "$99/mo" },
  enterprise: { label: "Enterprise Scale", price: "Custom" },
};

function SignUpContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { addTenant } = useTenant();

  const planKey = searchParams.get("plan") || "pro";
  const [selectedPlan, setSelectedPlan] = useState(planKey);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [loading, setLoading] = useState(false);

  const activePlan = planNames[selectedPlan] || planNames.pro;

  const handleSignUp = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const compName = company.trim() || "My Voice Operation";
    const tenant = addTenant(compName);

    localStorage.setItem(
      "voxflow_session",
      JSON.stringify({
        user: {
          name: name.trim() || "Operations Admin",
          email: email.trim() || "admin@company.com",
          tenant_id: tenant.id,
          plan: selectedPlan,
        },
        token: `demo-token-${Date.now()}`,
      })
    );

    setTimeout(() => {
      router.push("/dashboard");
    }, 400);
  };

  const handleDemoAccess = () => {
    setLoading(true);
    const tenant = addTenant("Varun Beverages (PepsiCo)");
    localStorage.setItem(
      "voxflow_session",
      JSON.stringify({
        user: {
          name: "Demo Admin",
          email: "demo@voxflow.ai",
          tenant_id: tenant.id,
          plan: "pro",
        },
        token: "demo-token-12345",
      })
    );
    router.push("/dashboard");
  };

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

        <form className="space-y-4" onSubmit={handleSignUp}>
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
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
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
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
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
              required
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="e.g. Apple, Shree Traders, ZenithTech"
              className="w-full px-4 py-3 rounded-xl bg-[#141422] border border-[#302840]/60 text-[#e8e0f0] text-sm placeholder:text-[#a098b0]/40 focus:outline-none focus:border-[#ff2d78] focus:ring-1 focus:ring-[#ff2d78]/40 transition-all font-body"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3.5 rounded-xl bg-[#ff2d78] text-[#1a0010] font-headline font-bold text-sm hover:shadow-[0_0_25px_rgba(255,45,120,0.5)] transition-all duration-200 active:scale-95 mt-2 disabled:opacity-50"
          >
            {loading ? "Activating Workspace..." : `Deploy ${activePlan.label} (${activePlan.price})`}
          </button>
        </form>

        <div className="mt-4 pt-4 border-t border-[#302840]/40 text-center">
          <button
            type="button"
            onClick={handleDemoAccess}
            className="w-full py-2.5 rounded-xl bg-[#1e1e30] border border-[#00ffcc]/30 text-[#00ffcc] font-label text-xs hover:bg-[#00ffcc]/10 transition-colors"
          >
            ⚡ Quick Demo Instant Login to Dashboard
          </button>
        </div>

        <p className="text-center text-xs font-label text-[#a098b0] mt-6">
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
