"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
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
    companyName: "Your Logistics Co",
    agentName: "Operations Assistant",
    language: "en",
    stats: { products: 3, suppliers: 1, stock_units: 190, orders: 1 },
  });

  const [agentName, setAgentName] = useState("Operations Assistant");
  const [greeting, setGreeting] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState<"en">("en");

  useEffect(() => {
    if (typeof window !== "undefined") {
      const raw = localStorage.getItem("voxflow_onboarding_data");
      if (raw) {
        try {
          const parsed = JSON.parse(raw);
          setData(parsed);
          setAgentName(parsed.agentName || "Operations Assistant");
          setSelectedLanguage("en");
          setGreeting(`Hello, and welcome to ${parsed.companyName}. How can I help with your delivery or dispatch today?`);
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
          name: `${data.companyName} Operations Lead`,
          tenant_id: data.tenantId,
        })
      );
      document.cookie = `auth-token=demo-user-${data.tenantId}; path=/; max-age=86400; SameSite=Lax`;
    }
    await refreshTenants().catch(() => {});
    router.push("/dashboard");
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-4 sm:px-6 pt-[5rem] pb-16 bg-[#030308] relative overflow-hidden selection:bg-[#5EEAD4]/30 selection:text-[#5EEAD4]">
      {/* Subtle background glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[32rem] h-[32rem] bg-[#5EEAD4]/5 blur-[140px] rounded-full pointer-events-none" />

      <div className="w-full max-w-2xl relative z-10">
        {/* Progress Bar Header */}
        <div className="mb-8">
          <div className="flex items-center justify-between text-xs font-mono uppercase tracking-widest text-white/50 mb-3">
            <span className={step >= 1 ? "text-[#5EEAD4] font-bold" : ""}>1. Persona</span>
            <span className={step >= 2 ? "text-[#5EEAD4] font-bold" : ""}>2. Starter Data</span>
            <span className={step >= 3 ? "text-[#5EEAD4] font-bold" : ""}>3. Test Voice</span>
            <span className={step >= 4 ? "text-[#5EEAD4] font-bold" : ""}>4. Launch</span>
          </div>
          <div className="w-full h-1 bg-white/[0.08] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#5EEAD4] transition-all duration-500 shadow-[0_0_10px_#5EEAD4]"
              style={{ width: `${(step / 4) * 100}%` }}
            />
          </div>
        </div>

        {/* Wizard Card Container */}
        <div className="rounded-3xl border border-white/[0.09] bg-[#0a0a12]/95 backdrop-blur-2xl p-6 sm:p-10 shadow-[inset_0_1px_1px_rgba(255,255,255,0.06),0_25px_50px_rgba(0,0,0,0.85)]">
          {/* STEP 1: Persona & Language */}
          {step === 1 && (
            <div>
              <div className="flex items-center gap-3 mb-4">
                <span className="p-2.5 rounded-xl bg-[#5EEAD4]/10 border border-[#5EEAD4]/30 text-xl text-[#5EEAD4]">
                  🎙️
                </span>
                <div>
                  <h2 className="font-headline font-bold text-2xl text-white">Voice Agent Configuration</h2>
                  <p className="text-xs text-white/50 font-sans mt-0.5">Customize your AI agent&apos;s identity for {data.companyName}.</p>
                </div>
              </div>

              <div className="space-y-4 my-6">
                <div>
                  <label className="text-xs font-mono uppercase tracking-widest text-white/80 block mb-1.5">
                    Agent Persona Name
                  </label>
                  <input
                    type="text"
                    value={agentName}
                    onChange={(e) => setAgentName(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl bg-[#11111a] border border-white/[0.08] text-white text-sm focus:outline-none focus:border-[#5EEAD4] transition-all font-sans"
                    placeholder="e.g. Operations Assistant, Sara, Alex"
                  />
                </div>

                <div>
                  <label className="text-xs font-mono uppercase tracking-widest text-white/80 block mb-1.5">
                    Agent Language & Dialect
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => setSelectedLanguage("en")}
                      className="p-3.5 rounded-xl border text-left transition-all border-[#5EEAD4] bg-[#5EEAD4]/10 text-[#5EEAD4] shadow-[0_0_15px_rgba(94,234,212,0.15)]"
                    >
                      <div className="text-sm font-bold flex items-center gap-1.5 text-white">🇬🇧 UK English (en-GB)</div>
                      <div className="text-[11px] text-white/50 mt-1">Natural British English, automated tool calls</div>
                    </button>
                    <button
                      type="button"
                      onClick={() => setSelectedLanguage("en")}
                      className="p-3.5 rounded-xl border text-left transition-all border-white/[0.08] bg-white/[0.02] text-white/70 hover:border-white/20"
                    >
                      <div className="text-sm font-bold flex items-center gap-1.5 text-white">🌐 Global English (en-US)</div>
                      <div className="text-[11px] text-white/50 mt-1">International freight & logistics dialect</div>
                    </button>
                  </div>
                </div>

                <div>
                  <label className="text-xs font-mono uppercase tracking-widest text-white/80 block mb-1.5">
                    Opening Greeting
                  </label>
                  <textarea
                    rows={2}
                    value={greeting}
                    onChange={(e) => setGreeting(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-xl bg-[#11111a] border border-white/[0.08] text-white text-sm focus:outline-none focus:border-[#5EEAD4] transition-all font-sans resize-none"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 mt-8">
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="px-6 py-3 rounded-xl bg-[#5EEAD4] text-[#030308] font-headline font-bold text-sm hover:shadow-[0_0_20px_rgba(94,234,212,0.5)] transition-all duration-200 active:scale-95 cursor-pointer"
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
                <span className="p-2.5 rounded-xl bg-[#5EEAD4]/10 border border-[#5EEAD4]/30 text-xl text-[#5EEAD4]">
                  📦
                </span>
                <div>
                  <h2 className="font-headline font-bold text-2xl text-white">Isolated Workspace Provisioned</h2>
                  <p className="text-xs text-white/50 font-sans mt-0.5">
                    Tenant ID: <span className="font-mono text-[#5EEAD4]">{data.tenantId}</span>
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 my-6">
                <div className="p-4 rounded-xl bg-[#11111a] border border-white/[0.06] text-center">
                  <div className="text-2xl font-mono font-bold text-[#5EEAD4]">{data.stats?.products || 3}</div>
                  <div className="text-[10px] text-white/50 uppercase font-mono mt-1">Products</div>
                </div>
                <div className="p-4 rounded-xl bg-[#11111a] border border-white/[0.06] text-center">
                  <div className="text-2xl font-mono font-bold text-white">{data.stats?.suppliers || 1}</div>
                  <div className="text-[10px] text-white/50 uppercase font-mono mt-1">Suppliers</div>
                </div>
                <div className="p-4 rounded-xl bg-[#11111a] border border-white/[0.06] text-center">
                  <div className="text-2xl font-mono font-bold text-emerald-400">{data.stats?.stock_units || 190}</div>
                  <div className="text-[10px] text-white/50 uppercase font-mono mt-1">Stock Units</div>
                </div>
                <div className="p-4 rounded-xl bg-[#11111a] border border-white/[0.06] text-center">
                  <div className="text-2xl font-mono font-bold text-[#5EEAD4]">{data.stats?.orders || 1}</div>
                  <div className="text-[10px] text-white/50 uppercase font-mono mt-1">Active POs</div>
                </div>
              </div>

              <div className="rounded-xl border border-white/[0.08] bg-[#11111a]/80 p-4 text-xs text-white space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-[#5EEAD4] font-bold">
                    <span>✓</span> Starter supply chain catalog pre-loaded
                  </div>
                  <button
                    type="button"
                    onClick={() => setModalOpen(true)}
                    className="text-[11px] font-mono text-[#5EEAD4] hover:underline flex items-center gap-1 cursor-pointer"
                  >
                    <span>+ Upload Custom CSV Instead</span>
                  </button>
                </div>
                <p className="text-white/60 text-[11px] leading-relaxed">
                  Your voice agent can immediately query stock levels, lookup tracking for PO-1001, and verify supplier credentials without any manual database setup.
                </p>
              </div>

              <div className="flex justify-between items-center gap-3 mt-8">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="px-4 py-2.5 rounded-xl border border-white/[0.08] bg-white/[0.02] text-xs text-white/70 hover:text-white cursor-pointer"
                >
                  ← Back
                </button>
                <button
                  type="button"
                  onClick={() => setStep(3)}
                  className="px-6 py-3 rounded-xl bg-[#5EEAD4] text-[#030308] font-headline font-bold text-sm hover:shadow-[0_0_20px_rgba(94,234,212,0.5)] transition-all duration-200 active:scale-95 cursor-pointer"
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
                <span className="p-2.5 rounded-xl bg-[#5EEAD4]/10 border border-[#5EEAD4]/30 text-xl text-[#5EEAD4]">
                  ⚡
                </span>
                <div>
                  <h2 className="font-headline font-bold text-2xl text-white">Try Your Voice Agent</h2>
                  <p className="text-xs text-white/50 font-sans mt-0.5">Test real-time voice latency and tool execution in your browser.</p>
                </div>
              </div>

              <div className="space-y-4 my-6">
                <div className="p-4 rounded-xl bg-[#11111a] border border-white/[0.08] space-y-3">
                  <div className="text-xs font-mono font-semibold text-[#5EEAD4] uppercase tracking-wider">
                    Recommended Test Prompts:
                  </div>
                  <div className="space-y-2 text-xs">
                    <div className="p-2.5 rounded-lg bg-[#030308] border border-white/[0.06] text-white/90 font-mono">
                      &quot;Hello, can you check our current inventory for cartons?&quot;
                    </div>
                    <div className="p-2.5 rounded-lg bg-[#030308] border border-white/[0.06] text-white/90 font-mono">
                      &quot;What is the status of purchase order PO-1001?&quot;
                    </div>
                  </div>
                </div>

                <Link
                  href="/dashboard/simulator"
                  target="_blank"
                  className="w-full py-3.5 rounded-xl border border-[#5EEAD4]/40 bg-[#5EEAD4]/10 text-[#5EEAD4] font-headline font-bold text-sm flex items-center justify-center gap-2 hover:bg-[#5EEAD4]/20 transition-all shadow-[0_0_20px_rgba(94,234,212,0.15)]"
                >
                  <span>📞</span> Launch Phone Simulator (New Tab) ↗
                </Link>
              </div>

              <div className="flex justify-between items-center gap-3 mt-8">
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="px-4 py-2.5 rounded-xl border border-white/[0.08] bg-white/[0.02] text-xs text-white/70 hover:text-white cursor-pointer"
                >
                  ← Back
                </button>
                <button
                  type="button"
                  onClick={() => setStep(4)}
                  className="px-6 py-3 rounded-xl bg-[#5EEAD4] text-[#030308] font-headline font-bold text-sm hover:shadow-[0_0_20px_rgba(94,234,212,0.5)] transition-all duration-200 active:scale-95 cursor-pointer"
                >
                  Ready to Launch →
                </button>
              </div>
            </div>
          )}

          {/* STEP 4: Ready / Go to Dashboard */}
          {step === 4 && (
            <div className="text-center py-4">
              <div className="h-16 w-16 rounded-2xl bg-[#5EEAD4]/15 border border-[#5EEAD4]/40 grid place-items-center text-3xl mx-auto mb-5 shadow-[0_0_30px_rgba(94,234,212,0.25)] text-[#5EEAD4]">
                🚀
              </div>
              <h2 className="font-headline font-bold text-3xl text-white">Workspace Ready!</h2>
              <p className="text-sm text-white/70 mt-2 max-w-md mx-auto font-sans leading-relaxed">
                <span className="text-[#5EEAD4] font-bold">{data.companyName}</span> is configured with isolated tenant access, 500 trial minutes, and ~200ms turn, UK edge voice runtime.
              </p>

              <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
                <button
                  type="button"
                  onClick={handleFinish}
                  className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-[#5EEAD4] text-[#030308] font-headline font-bold text-sm hover:shadow-[0_0_25px_rgba(94,234,212,0.5)] transition-all duration-200 active:scale-95 cursor-pointer"
                >
                  Enter Operations Dashboard →
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

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
