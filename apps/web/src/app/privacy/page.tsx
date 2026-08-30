import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy | VoxFlow Voice Agent",
  description: "UK GDPR & Data Protection Act 2018 compliance notice and privacy policy for VoxFlow.",
};

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-teal-500/30 selection:text-teal-200">
      <header className="border-b border-slate-800/80 bg-slate-900/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-bold text-lg text-white">
            <span className="w-8 h-8 rounded-lg bg-gradient-to-tr from-teal-500 to-indigo-600 flex items-center justify-center font-black shadow-lg shadow-teal-500/20">
              V
            </span>
            <span>VoxFlow</span>
          </Link>
          <div className="flex items-center gap-4 text-sm font-medium">
            <Link href="/pricing" className="text-slate-400 hover:text-white transition">Pricing</Link>
            <Link href="/sign-in" className="text-slate-400 hover:text-white transition">Sign In</Link>
            <Link href="/sign-up" className="bg-teal-500 hover:bg-teal-400 text-slate-950 px-3.5 py-1.5 rounded-lg font-semibold transition">
              Start Free Trial
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-16">
        <div className="mb-12 border-b border-slate-800 pb-8">
          <span className="text-teal-400 text-xs font-bold uppercase tracking-wider bg-teal-950/60 border border-teal-800/50 px-2.5 py-1 rounded-full">
            UK GDPR & Data Protection
          </span>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white mt-4 tracking-tight">
            Privacy Policy
          </h1>
          <p className="text-slate-400 text-sm mt-2">Compliance: UK GDPR & Data Protection Act 2018 • Region: EU/UK (London eu-west-2)</p>
        </div>

        <div className="space-y-10 text-slate-300 leading-relaxed text-sm sm:text-base">
          <section className="space-y-3">
            <h2 className="text-xl font-bold text-white tracking-tight">1. Overview & Data Controller vs. Data Processor</h2>
            <p>
              VoxFlow Technologies Ltd acts as a <strong>Data Processor</strong> on behalf of our enterprise customers (the <strong>Data Controllers</strong>) who use our automated telephony services. We process caller information strictly in accordance with documented instructions from our customers.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-bold text-white tracking-tight">2. Information We Collect</h2>
            <ul className="list-disc list-inside space-y-1.5 text-slate-400 ml-2">
              <li><strong>Account Data:</strong> Business email, contact name, billing details, and company identifiers.</li>
              <li><strong>Telephony Metadata:</strong> Inbound/outbound caller E.164 phone numbers (masked at rest and in logs), timestamps, call duration, and call resolution statuses.</li>
              <li><strong>Conversational Transcripts:</strong> Audio transcripts generated during live calls, subject to configurable automated retention schedules (default 30-day purge).</li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-bold text-white tracking-tight">3. Data Retention & Automated Purge Policy</h2>
            <p>
              VoxFlow enforces strict automated data lifecycle policies. Expired call transcripts and recording pointers are permanently erased via automated daily cron jobs, and caller PII is scrubbed in compliance with customer-configured retention limits.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-bold text-white tracking-tight">4. Data Subject Rights (DSAR & Right to Erasure)</h2>
            <p>
              In accordance with UK GDPR Chapter 3, individuals have the right to request:
            </p>
            <ul className="list-disc list-inside space-y-1 text-slate-400 ml-2">
              <li><strong>Right of Access (DSAR Export):</strong> Complete JSON bundle of all stored interactions associated with a phone number or email address.</li>
              <li><strong>Right to be Forgotten (Erasure):</strong> Permanent anonymization and redaction of caller PII while preserving non-PII financial and inventory records.</li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-bold text-white tracking-tight">5. Sub-Processors & Data Sovereignty</h2>
            <p>
              Our infrastructure utilizes trusted, ISO27001/SOC2-certified cloud sub-processors including Amazon Web Services (AWS eu-west-2), Supabase (London PostgreSQL), and Stripe Payments UK Ltd.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-bold text-white tracking-tight">6. Data Protection Officer (DPO)</h2>
            <p>
              To exercise data subject rights or submit privacy queries, email our Data Protection Officer at <a href="mailto:dpo@voxflow.ai" className="text-teal-400 hover:underline">dpo@voxflow.ai</a>.
            </p>
          </section>
        </div>
      </main>

      <footer className="border-t border-slate-800/80 py-8 bg-slate-900/30 text-center text-xs text-slate-500">
        <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p>© 2026 VoxFlow Technologies Ltd. All rights reserved.</p>
          <div className="flex items-center gap-6">
            <Link href="/terms" className="hover:text-slate-300 transition">Terms of Service</Link>
            <Link href="/privacy" className="hover:text-slate-300 transition">Privacy Policy</Link>
            <Link href="/refund" className="hover:text-slate-300 transition">Refund Policy</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
