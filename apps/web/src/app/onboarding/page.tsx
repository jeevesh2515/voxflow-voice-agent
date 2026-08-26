"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { useEffect, useState } from "react";
import { FadeUp } from "@/components/ScrollAnimations";
import { useAuth } from "@/lib/auth-context";
import { useTenant } from "@/lib/tenant-context";
import CsvImportModal from "@/components/dashboard/CsvImportModal";

type OnboardingData = {
  tenantId: string;
  companyName: string;
  agentName: string;
  language: string;
  stats?: {
    products: number;
    suppliers: number;
    stock_units: number;
    orders: number;
  };
};

export default function OnboardingPage() {
  const router = useRouter();
  const { user } = useAuth();
  const { refreshTenants, setActiveTenantId } = useTenant();
  const [step, setStep] = useState<1 | 2 | 3 | 4>(1);
  const [modalOpen, setModalOpen] = useState(false);
  const [data, setData] = useState<OnboardingData>({
    tenantId: "workspace",
    companyName: "Your Company",
    agentName: "Vaani",
    language: "en",
    stats: { products: 3, suppliers: 1, stock_units: 190, orders: 1 },
  });


  const [agentName, setAgentName] = useState("Vaani");
  const [greeting, setGreeting] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState<"en" | "hi">("en");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const raw = localStorage.getItem("voxflow_onboarding_data");
      if (raw) {
        try {
          const parsed = JSON.parse(raw);
          setData(parsed);
          setAgentName(parsed.agentName || "Vaani");
          setSelectedLanguage(parsed.language === "hi" ? "hi" : "en");
          setGreeting(`Hello, and welcome to ${parsed.companyName}. How can I help you today?`);
          if (parsed.tenantId) {
            setActiveTenantId(parsed.tenantId);
          }
        } catch (e) {
          console.error("Failed to parse onboarding cache", e);
        }
      }
      refreshTenants().catch(() => {});
    }
  }, [refreshTenants, setActiveTenantId]);

  const handleFinish = async () => {
    if (typeof window !== "undefined") {
      localStorage.setItem("voxflow_active_tenant", data.tenantId);
      localStorage.setItem("voxflow_demo_tenant", data.tenantId);
      localStorage.setItem(
        "voxflow_demo_user",
        JSON.stringify({
          id: `owner-${data.tenantId}`,
          email: `${data.tenantId}@voxflow.invalid`,
          name: `${data.companyName} Owner`,
          tenant_id: data.tenantId,
        })
      );
      document.cookie = `voxflow_demo_user=${encodeURIComponent(
        JSON.stringify({
          id: `owner-${data.tenantId}`,
          email: "demo@voxflow.invalid",
          name: `${data.companyName} Owner`,
          tenant_id: "varun",
        })
      )}; path=/; max-age=86400`;
    }
    await refreshTenants().catch(() => {});
    router.push("/dashboard");
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 sm:px-6 pt-[5rem] pb-16 bg-[#0a0a12] grid-bg relative overflow-hidden">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[32rem] h-[32rem] bg-[#00ffcc]/10 blur-[140px] rounded-full pointer-events-none" />

      <FadeUp className="w-full max-w-2xl relative z-10">
        {/* Progress Bar Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between text-xs font-label uppercase tracking-wider text-[#a098b0] mb-3">
            <span className={step >= 1 ? "text-[#00ffcc] font-bold" : ""}>1. Workspace Persona</span>
            <span className={step >= 2 ? "text-[#00ffcc] font-bold" : ""}>2. Starter Data</span>
            <span className={step >= 3 ? "text-[#00ffcc] font-bold" : ""}>3. Test Agent</span>
            <span className={step >= 4 ? "text-[#00ffcc] font-bold" : ""}>4. Launch</span>
          </div>
          <div className="w-full h-1.5 bg-[#1e1a2e] rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-[#ff2d78] to-[#00ffcc] transition-all duration-500"
              style={{ width: `${(step / 4) * 100}%` }}
            />
          </div>
        </div>

        {/* Wizard Card Container */}
        <div className="glass neon-border rounded-2xl p-6 sm:p-10 border border-[#00ffcc]/30 shadow-[0_0_50px_rgba(0,0,0,0.5)]">
          {/* STEP 1: Persona & Language */}
          {step === 1 && (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <span className="p-2 rounded-xl bg-[#00ffcc]/10 border border-[#00ffcc]/30 text-xl">🎙️</span>
                <div>
                  <h2 className="font-headline font-bold text-2xl text-[#e8e0f0]">Voice Agent Configuration</h2>
                  <p className="text-xs text-[#a098b0] font-body mt-0.5">Customize your AI agent&apos;s identity for {data.companyName}.</p>
                </div>
              </div>

              <div className="space-y-4 my-6">
                <div>
                  <label className="text-xs font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                    Agent Persona Name
                  </label>
                  <input
                    type="text"
                    value={agentName}
                    onChange={(e) => setAgentName(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl bg-[#141422] border border-[#302840]/60 text-[#e8e0f0] text-sm focus:outline-none focus:border-[#00ffcc] transition-all font-body"
                    placeholder="e.g. Vaani, Sara, Alex"
                  />
                </div>

                <div>
                  <label className="text-xs font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                    Primary Operational Language
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => setSelectedLanguage("en")}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        selectedLanguage === "en"
                          ? "border-[#00ffcc] bg-[#00ffcc]/10 text-[#00ffcc]"
                          : "border-[#302840]/60 bg-[#141422] text-[#a098b0]"
                      }`}
                    >
                      <div className="text-sm font-bold flex items-center gap-1.5">🇬🇧 UK English (en)</div>
                      <div className="text-[10px] text-[#a098b0] mt-1">Natural British English, automated tool calls</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => setSelectedLanguage("hi")}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        selectedLanguage === "hi"
                          ? "border-[#ff2d78] bg-[#ff2d78]/10 text-[#ff2d78]"
                          : "border-[#302840]/60 bg-[#141422] text-[#a098b0]"
                      }`}
                    >
                      <div className="text-sm font-bold flex items-center gap-1.5">🇮🇳 Hindi (hi)</div>
                      <div className="text-[10px] text-[#a098b0] mt-1">Natural Devanagari Hindi with English fallback</div>
                    </button>
                  </div>
                </div>

                <div>
                  <label className="text-xs font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                    Opening Greeting
                  </label>
                  <textarea
                    rows={2}
                    value={greeting}
                    onChange={(e) => setGreeting(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-[#141422] border border-[#302840]/60 text-[#e8e0f0] text-sm focus:outline-none focus:border-[#00ffcc] transition-all font-body resize-none"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 mt-8">
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="px-6 py-3 rounded-xl bg-[#00ffcc] text-[#0a0a12] font-headline font-bold text-sm hover:shadow-[0_0_20px_rgba(0,255,204,0.5)] transition-all duration-200"
                >
                  Continue to Starter Data →
                </button>
              </div>
            </div>
          )}

          {/* STEP 2: Starter Catalog & Data */}
          {step === 2 && (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <span className="p-2 rounded-xl bg-[#00ffcc]/10 border border-[#00ffcc]/30 text-xl">📦</span>
                <div>
                  <h2 className="font-headline font-bold text-2xl text-[#e8e0f0]">Isolated Workspace Provisioned</h2>
                  <p className="text-xs text-[#a098b0] font-body mt-0.5">
                    Tenant ID: <span className="font-mono text-[#00ffcc]">{data.tenantId}</span>
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 my-6">
                <div className="p-4 rounded-xl bg-[#141422] border border-[#302840]/60 text-center">
                  <div className="text-2xl font-mono font-bold text-[#00ffcc]">{data.stats?.products || 3}</div>
                  <div className="text-[11px] text-[#a098b0] uppercase font-label mt-1">Products</div>
                </div>
                <div className="p-4 rounded-xl bg-[#141422] border border-[#302840]/60 text-center">
                  <div className="text-2xl font-mono font-bold text-[#ff2d78]">{data.stats?.suppliers || 1}</div>
                  <div className="text-[11px] text-[#a098b0] uppercase font-label mt-1">Suppliers</div>
                </div>
                <div className="p-4 rounded-xl bg-[#141422] border border-[#302840]/60 text-center">
                  <div className="text-2xl font-mono font-bold text-[#ffe04a]">{data.stats?.stock_units || 190}</div>
                  <div className="text-[11px] text-[#a098b0] uppercase font-label mt-1">Stock Units</div>
                </div>
                <div className="p-4 rounded-xl bg-[#141422] border border-[#302840]/60 text-center">
                  <div className="text-2xl font-mono font-bold text-[#a78bfa]">{data.stats?.orders || 1}</div>
                  <div className="text-[11px] text-[#a098b0] uppercase font-label mt-1">Active POs</div>
                </div>
              </div>

              <div className="rounded-xl border border-[#302840]/60 bg-[#141422]/60 p-4 text-xs text-[#e8e0f0] space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-[#00ffcc] font-bold">
                    <span>✓</span> Starter supply chain catalog pre-loaded
                  </div>
                  <button
                    type="button"
                    onClick={() => setModalOpen(true)}
                    className="text-[11px] font-mono text-[#00ffcc] hover:underline flex items-center gap-1"
                  >
                    <span>+ Upload Custom CSV Instead</span>
                  </button>
                </div>
                <p className="text-[#a098b0] text-[11px]">
                  Your voice agent can immediately query stock levels, lookup tracking for PO-1001, and verify supplier credentials without any manual database setup.
                </p>
              </div>

              <div className="flex justify-between items-center gap-3 mt-8">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="px-4 py-2.5 rounded-xl border border-[#302840] text-xs text-[#a098b0] hover:text-[#e8e0f0]"
                >
                  ← Back
                </button>
                <button
                  type="button"
                  onClick={() => setStep(3)}
                  className="px-6 py-3 rounded-xl bg-[#00ffcc] text-[#0a0a12] font-headline font-bold text-sm hover:shadow-[0_0_20px_rgba(0,255,204,0.5)] transition-all duration-200"
                >
                  Test Voice Agent Live →
                </button>
              </div>
            </div>
          )}


          {/* STEP 3: Live Simulator Test */}
          {step === 3 && (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <span className="p-2 rounded-xl bg-[#ff2d78]/10 border border-[#ff2d78]/30 text-xl">⚡</span>
                <div>
                  <h2 className="font-headline font-bold text-2xl text-[#e8e0f0]">Try Your Voice Agent</h2>
                  <p className="text-xs text-[#a098b0] font-body mt-0.5">Test real-time voice latency and tool execution in your browser.</p>
                </div>
              </div>

              <div className="space-y-4 my-6">
                <div className="p-4 rounded-xl bg-[#141422] border border-[#ff2d78]/30 space-y-3">
                  <div className="text-xs font-semibold text-[#ff2d78] uppercase tracking-wider">
                    Recommended Test Prompts:
                  </div>
                  <div className="space-y-2 text-xs">
                    <div className="p-2.5 rounded-lg bg-[#0a0a12] border border-[#302840]/60 text-[#e8e0f0] font-mono">
                      &quot;Hello, can you check our current inventory for cartons?&quot;
                    </div>
                    <div className="p-2.5 rounded-lg bg-[#0a0a12] border border-[#302840]/60 text-[#e8e0f0] font-mono">
                      &quot;What is the status of purchase order PO-1001?&quot;
                    </div>
                  </div>
                </div>

                <Link
                  href="/dashboard/simulator"
                  target="_blank"
                  className="w-full py-3.5 rounded-xl border border-[#00ffcc] bg-[#00ffcc]/10 text-[#00ffcc] font-headline font-bold text-sm flex items-center justify-center gap-2 hover:bg-[#00ffcc]/20 transition-all shadow-[0_0_20px_rgba(0,255,204,0.2)]"
                >
                  <span>📞</span> Launch Phone Simulator (New Tab) ↗
                </Link>
              </div>

              <div className="flex justify-between items-center gap-3 mt-8">
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="px-4 py-2.5 rounded-xl border border-[#302840] text-xs text-[#a098b0] hover:text-[#e8e0f0]"
                >
                  ← Back
                </button>
                <button
                  type="button"
                  onClick={() => setStep(4)}
                  className="px-6 py-3 rounded-xl bg-[#ff2d78] text-[#1a0010] font-headline font-bold text-sm hover:shadow-[0_0_20px_rgba(255,45,120,0.5)] transition-all duration-200"
                >
                  Ready to Launch →
                </button>
              </div>
            </div>
          )}

          {/* STEP 4: Ready / Go to Dashboard */}
          {step === 4 && (
            <div className="text-center py-4">
              <div className="h-16 w-16 rounded-2xl bg-gradient-to-tr from-[#ff2d78] to-[#00ffcc] grid place-items-center text-3xl mx-auto mb-5 shadow-[0_0_30px_rgba(0,255,204,0.4)]">
                🚀
              </div>
              <h2 className="font-headline font-bold text-3xl text-[#e8e0f0]">Workspace Ready!</h2>
              <p className="text-sm text-[#a098b0] mt-2 max-w-md mx-auto font-body">
                {data.companyName} is set up with owner authorization and isolated tenant access.
              </p>

              <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
                <button
                  type="button"
                  onClick={handleFinish}
                  className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-[#00ffcc] text-[#0a0a12] font-headline font-bold text-sm hover:shadow-[0_0_25px_rgba(0,255,204,0.5)] transition-all duration-200"
                >
                  Enter Operations Dashboard →
                </button>
              </div>
            </div>
          )}
        </div>
      </FadeUp>

      <CsvImportModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        initialEntity="products"
        onSuccess={() => {
          setData((prev) => ({
            ...prev,
            stats: {
              ...prev.stats,
              products: (prev.stats?.products || 0) + 1,
              suppliers: prev.stats?.suppliers || 1,
              stock_units: (prev.stats?.stock_units || 0) + 50,
              orders: prev.stats?.orders || 1,
            },
          }));
        }}
      />
    </div>
  );
}

