import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy Policy | Voxflow Voice Agent",
  description: "UK GDPR & Data Protection Act 2018 compliance notice and privacy policy for Voxflow.",
};

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-[#030308] text-white selection:bg-[#5EEAD4]/30 selection:text-[#5EEAD4]">
      <header className="border-b border-white/[0.06] bg-[#030308]/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 font-headline font-bold text-lg text-white">
            <span className="w-7 h-7 rounded-lg bg-[#5EEAD4]/10 border border-[#5EEAD4]/30 text-[#5EEAD4] flex items-center justify-center font-black">
              V
            </span>
            <span>VOX<span className="text-[#5EEAD4]">FLOW</span></span>
          </Link>
          <div className="flex items-center gap-4 text-xs font-mono">
            <Link href="/pricing" className="text-white/60 hover:text-white transition">Pricing</Link>
            <Link href="/sign-in" className="text-white/60 hover:text-white transition">Sign In</Link>
            <Link href="/sign-up" className="bg-[#5EEAD4] hover:bg-[#5EEAD4]/90 text-[#030308] px-3.5 py-1.5 rounded-lg font-bold transition">
              Start Free Trial
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-16">
        <div className="mb-12 border-b border-white/[0.06] pb-8">
          <span className="text-[#5EEAD4] text-xs font-mono font-bold uppercase tracking-wider bg-[#5EEAD4]/10 border border-[#5EEAD4]/30 px-3 py-1 rounded-full">
            UK GDPR &amp; Data Protection
          </span>
          <h1 className="text-3xl sm:text-4xl font-headline font-extrabold text-white mt-4 tracking-tight">
            Privacy Policy
          </h1>
          <p className="text-white/50 text-xs font-mono mt-2">Compliance: UK GDPR &amp; Data Protection Act 2018 • Region: EU/UK (London eu-west-2)</p>
        </div>

        <div className="space-y-10 text-white/70 leading-relaxed text-sm sm:text-base font-sans">
          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">1. Overview &amp; Data Controller vs. Data Processor</h2>
            <p>
              Voxflow Technologies Ltd acts as a <strong>Data Processor</strong> on behalf of our enterprise customers (the <strong>Data Controllers</strong>) who use our automated telephony services. We process caller information strictly in accordance with documented instructions from our customers.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">2. Information We Collect</h2>
            <ul className="list-disc list-inside space-y-1.5 text-white/60 ml-2">
              <li><strong>Account Data:</strong> Business email, contact name, billing details, and company identifiers.</li>
              <li><strong>Telephony Metadata:</strong> Inbound/outbound caller E.164 phone numbers (masked at rest and in logs), timestamps, call duration, and call resolution statuses.</li>
              <li><strong>Conversational Transcripts:</strong> Audio transcripts generated during live calls, subject to configurable automated retention schedules (default 30-day purge).</li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">3. Data Retention &amp; Automated Purge Policy</h2>
            <p>
              Voxflow enforces strict automated data lifecycle policies. Expired call transcripts and recording pointers are permanently erased via automated daily cron jobs, and caller PII is scrubbed in compliance with customer-configured retention limits.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">4. Data Subject Rights (DSAR &amp; Right to Erasure)</h2>
            <p>
              In accordance with UK GDPR Chapter 3, individuals have the right to request:
            </p>
            <ul className="list-disc list-inside space-y-1 text-white/60 ml-2">
              <li><strong>Right of Access (DSAR Export):</strong> Complete JSON bundle of all stored interactions associated with a phone number or email address.</li>
              <li><strong>Right to be Forgotten (Erasure):</strong> Permanent anonymization and redaction of caller PII while preserving non-PII financial and inventory records.</li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">5. Sub-Processors &amp; Data Sovereignty</h2>
            <p>
              Our infrastructure utilizes trusted, ISO27001-certified and UK GDPR-compliant cloud sub-processors including Amazon Web Services (AWS eu-west-2), Supabase (London PostgreSQL), and Stripe Payments UK Ltd.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">6. Data Protection Officer (DPO)</h2>
            <p>
              To exercise data subject rights or submit privacy queries, email our Data Protection Officer at <a href="mailto:dpo@voxflow.ai" className="text-[#5EEAD4] hover:underline">dpo@voxflow.ai</a>.
            </p>
          </section>
        </div>
      </main>

      <footer className="border-t border-white/[0.06] py-8 bg-[#030308]/90 text-center text-xs text-white/40 font-mono">
        <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p>&copy; 2026 Voxflow Technologies Ltd. All rights reserved.</p>
          <div className="flex items-center gap-6">
            <Link href="/terms" className="hover:text-white transition">Terms of Service</Link>
            <Link href="/privacy" className="hover:text-white transition">Privacy Policy</Link>
            <Link href="/refund" className="hover:text-white transition">Refund Policy</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
