"use client";

import { useState } from "react";
import Link from "next/link";
import {
  BookOpen,
  Terminal,
  PhoneCall,
  ShieldCheck,
  CreditCard,
  Webhook,
  Search,
  ExternalLink,
  ChevronRight,
  Code2,
  Copy,
  Check,
} from "lucide-react";

type DocSection = "quickstart" | "telephony" | "api" | "billing" | "webhooks";

export default function DocsPage() {
  const [activeSection, setActiveSection] = useState<DocSection>("quickstart");
  const [copied, setCopied] = useState<string | null>(null);

  const copyCode = (code: string, id: string) => {
    navigator.clipboard.writeText(code);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div className="min-h-screen bg-[#07070f] text-[#e8e0f0] font-sans selection:bg-[#00ffcc] selection:text-[#07070f]">
      {/* Docs Header */}
      <header className="border-b border-[#1e1e30] bg-[#0c0c16]/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="font-headline font-black text-xl text-white tracking-tight flex items-center gap-2">
              <span className="text-[#ff2d78]">VOX</span>FLOW
              <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-[#ff2d78]/10 text-[#ff2d78] border border-[#ff2d78]/20">
                DOCS
              </span>
            </Link>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="text-xs font-mono font-medium text-[#94a3b8] hover:text-white px-3 py-1.5 rounded-lg border border-[#28283c] hover:border-[#00ffcc]/40 transition-colors"
            >
              Operations Console →
            </Link>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-10 items-start">
          {/* Sidebar Navigation */}
          <aside className="space-y-6 lg:sticky lg:top-24">
            <div>
              <div className="text-[11px] font-mono uppercase tracking-widest text-[#706880] mb-3 font-bold">
                Platform Architecture
              </div>
              <nav className="space-y-1">
                {[
                  { id: "quickstart", label: "Getting Started", icon: BookOpen },
                  { id: "telephony", label: "Amazon Connect UK", icon: PhoneCall },
                  { id: "api", label: "REST API & Bearer Auth", icon: Code2 },
                  { id: "billing", label: "Billing & Metering", icon: CreditCard },
                  { id: "webhooks", label: "Webhooks & DLQ", icon: Webhook },
                ].map((item) => {
                  const Icon = item.icon;
                  const active = activeSection === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => setActiveSection(item.id as DocSection)}
                      className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-medium transition-all text-left cursor-pointer ${
                        active
                          ? "bg-[#ff2d78]/10 text-[#ff2d78] border border-[#ff2d78]/30 font-bold shadow-sm"
                          : "text-[#94a3b8] hover:text-white hover:bg-[#141424]"
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <Icon size={15} className={active ? "text-[#ff2d78]" : "text-[#706880]"} />
                        <span>{item.label}</span>
                      </div>
                      {active && <ChevronRight size={13} />}
                    </button>
                  );
                })}
              </nav>
            </div>

            <div className="p-4 rounded-xl bg-[#10101c] border border-[#202034] space-y-2">
              <div className="text-[11px] font-bold text-white flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-[#00ffcc] animate-pulse" />
                Live Status
              </div>
              <p className="text-[11px] text-[#94a3b8] leading-relaxed">
                AWS eu-west-2, Amazon Connect, and RDS PostgreSQL operational.
              </p>
              <Link href="/status" className="inline-flex items-center gap-1 text-[11px] font-mono text-[#00ffcc] hover:underline pt-1">
                View Status Page ↗
              </Link>
            </div>
          </aside>

          {/* Main Content Area */}
          <main className="space-y-8 bg-[#0c0c16] border border-[#202034] rounded-2xl p-6 sm:p-10 shadow-xl">
            {activeSection === "quickstart" && (
              <div className="space-y-6 animate-fade-in">
                <div>
                  <span className="text-[11px] font-mono text-[#ff2d78] uppercase tracking-wider font-bold">Phase 3 — Operational Trust</span>
                  <h1 className="text-2xl sm:text-3xl font-headline font-black text-white mt-1">Getting Started with VoxFlow</h1>
                  <p className="text-sm text-[#cbd5e1] leading-relaxed mt-2">
                    VoxFlow provides high-stakes autonomous voice operations for UK freight, logistics, and dispatch teams.
                    Voice agents complete two-way inventory checks, reserve dock loading bays, and verify caller identities in under 200ms.
                  </p>
                </div>

                <div className="space-y-4">
                  <h2 className="text-lg font-headline font-bold text-white">Three-Minute Quickstart</h2>
                  <ol className="list-decimal list-inside space-y-3 text-sm text-[#cbd5e1]">
                    <li>
                      <strong className="text-white">Create your workspace:</strong> Sign up at <Link href="/sign-up" className="text-[#00ffcc] hover:underline">/sign-up</Link> and specify your transport company name.
                    </li>
                    <li>
                      <strong className="text-white">Launch the simulator:</strong> Navigate to <Link href="/dashboard/simulator" className="text-[#00ffcc] hover:underline">/dashboard/simulator</Link> to speak directly with Charlotte (British English persona) via WebAudio.
                    </li>
                    <li>
                      <strong className="text-white">Assign a dedicated UK DID:</strong> Go to <Link href="/dashboard/settings" className="text-[#00ffcc] hover:underline">Settings → Telephony</Link> to route inbound +44 numbers directly into Amazon Connect.
                    </li>
                  </ol>
                </div>

                <div className="p-4 rounded-xl bg-[#141424] border border-[#28283c] space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-mono font-bold text-[#00ffcc]">CLI Diagnostic Preflight Check</span>
                    <button
                      onClick={() => copyCode("curl -s https://voxflow-voice-agent.vercel.app/api/health", "cli-preflight")}
                      className="text-xs font-mono text-[#94a3b8] hover:text-white flex items-center gap-1 cursor-pointer"
                    >
                      {copied === "cli-preflight" ? <Check size={13} className="text-[#00ffcc]" /> : <Copy size={13} />}
                      <span>Copy</span>
                    </button>
                  </div>
                  <pre className="text-xs font-mono text-[#f8fafc] bg-[#090912] p-3 rounded-lg overflow-x-auto">
                    curl -s https://voxflow-voice-agent.vercel.app/api/health
                  </pre>
                </div>
              </div>
            )}

            {activeSection === "telephony" && (
              <div className="space-y-6 animate-fade-in">
                <div>
                  <span className="text-[11px] font-mono text-[#00ffcc] uppercase tracking-wider font-bold">AWS eu-west-2 Architecture</span>
                  <h1 className="text-2xl sm:text-3xl font-headline font-black text-white mt-1">Amazon Connect UK Integration</h1>
                  <p className="text-sm text-[#cbd5e1] leading-relaxed mt-2">
                    VoxFlow pairs Amazon Connect contact flows with fine-tuned British English speech models. Incoming caller audio streams through our HMAC-authenticated AWS Lambda bridge directly into Groq Whisper and LLM inference.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl bg-[#141424] border border-[#242438]">
                    <div className="text-xs font-bold text-white">Exact DID Inbound Routing</div>
                    <p className="text-xs text-[#94a3b8] mt-1">
                      Tenant context is strictly isolated. Calls arriving on unknown destination numbers return <code className="text-[#ff2d78]">unknown_connect_did</code> and terminate immediately without data leakage.
                    </p>
                  </div>
                  <div className="p-4 rounded-xl bg-[#141424] border border-[#242438]">
                    <div className="text-xs font-bold text-white">Dual-Channel S3 &amp; DLQ</div>
                    <p className="text-xs text-[#94a3b8] mt-1">
                      Call recordings are ingested into encrypted S3 buckets in London with 24-hour retention. Failed chunks automatically divert to SQS DLQ for audit replay.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {activeSection === "api" && (
              <div className="space-y-6 animate-fade-in">
                <div>
                  <span className="text-[11px] font-mono text-[#38bdf8] uppercase tracking-wider font-bold">REST Contracts</span>
                  <h1 className="text-2xl sm:text-3xl font-headline font-black text-white mt-1">REST API &amp; Bearer Authentication</h1>
                  <p className="text-sm text-[#cbd5e1] leading-relaxed mt-2">
                    All operations are scoped to an authenticated tenant workspace. Pass your Supabase session JWT in the <code className="text-[#38bdf8]">Authorization: Bearer &lt;token&gt;</code> header.
                  </p>
                </div>

                <div className="space-y-3">
                  <div className="text-xs font-mono text-[#94a3b8] uppercase font-bold">Example: Query Escalation Queue</div>
                  <pre className="text-xs font-mono text-[#f8fafc] bg-[#090912] p-4 rounded-xl border border-[#202034] overflow-x-auto">
{`curl -X GET "https://voxflow-voice-agent.vercel.app/api/tenants/your-workspace/escalations" \\
  -H "Authorization: Bearer \${VOXFLOW_JWT}" \\
  -H "Content-Type: application/json"`}
                  </pre>
                </div>
              </div>
            )}

            {activeSection === "billing" && (
              <div className="space-y-6 animate-fade-in">
                <div>
                  <span className="text-[11px] font-mono text-[#ffe04a] uppercase tracking-wider font-bold">Stripe Meters &amp; VAT</span>
                  <h1 className="text-2xl sm:text-3xl font-headline font-black text-white mt-1">Billing, Invoices &amp; Metering</h1>
                  <p className="text-sm text-[#cbd5e1] leading-relaxed mt-2">
                    VoxFlow bills in GBP (£) with automated 20% UK VAT receipts. Every call turn reports exact metered call minutes to Stripe Billing Meters.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-[#141424] border border-[#242438] space-y-2">
                  <div className="text-xs font-bold text-white">Tier Specifications</div>
                  <ul className="text-xs text-[#cbd5e1] space-y-1.5 list-disc list-inside">
                    <li><strong>Starter (£149/mo):</strong> 750 call mins included, 1 line, 15p/min overage.</li>
                    <li><strong>Growth (£449/mo):</strong> 3,000 call mins included, 3 lines, 12p/min overage, PIN verification.</li>
                    <li><strong>Enterprise (£1,499/mo):</strong> 12,000 call mins included, unlimited lines, 24/7 SLA.</li>
                  </ul>
                </div>
              </div>
            )}

            {activeSection === "webhooks" && (
              <div className="space-y-6 animate-fade-in">
                <div>
                  <span className="text-[11px] font-mono text-[#ff2d78] uppercase tracking-wider font-bold">Integrations</span>
                  <h1 className="text-2xl sm:text-3xl font-headline font-black text-white mt-1">Webhooks &amp; Real-time Alerts</h1>
                  <p className="text-sm text-[#cbd5e1] leading-relaxed mt-2">
                    Receive immediate notifications when call turns complete, stock levels dip, or human operator escalations are created.
                  </p>
                </div>

                <div className="p-4 rounded-xl bg-[#141424] border border-[#242438]">
                  <div className="text-xs font-bold text-white">Transactional Resend Webhooks</div>
                  <p className="text-xs text-[#94a3b8] mt-1">
                    All payment confirmations and password resets dispatch through typed Resend templates with verifiable delivery telemetry.
                  </p>
                </div>
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
