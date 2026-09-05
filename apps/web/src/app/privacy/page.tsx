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

        <div className="mb-8 rounded-lg border border-[#5EEAD4]/30 bg-[#5EEAD4]/10 px-4 py-3 text-sm text-white/80">
          <p>
            <strong className="font-bold text-white">Template notice:</strong> This document is template-based, does not constitute legal advice, is pending solicitor review, and must not be relied on for real contracts or payments.
          </p>
          <p className="mt-1">
            Drafted with AI assistance; requires solicitor sign-off before use with paying customers.
          </p>
        </div>

        <div className="space-y-10 text-white/70 leading-relaxed text-sm sm:text-base font-sans">
          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">1. Overview &amp; Data Controller vs. Data Processor</h2>
            <p>
              Voxflow Technologies Ltd acts as a <strong>Data Processor</strong> on behalf of our enterprise customers (the <strong>Data Controllers</strong>) who use our automated telephony services. We process caller information strictly in accordance with documented instructions from our customers. Where Voxflow determines the purposes and means of processing its own business data (for example, Customer account administration), it acts as Controller for that data.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">2. Information We Collect</h2>
            <ul className="list-disc list-inside space-y-1.5 text-white/60 ml-2">
              <li><strong>Account Data:</strong> Business email, contact name, billing details, and company identifiers.</li>
              <li><strong>Telephony Metadata:</strong> Inbound/outbound caller E.164 phone numbers (masked at rest and in logs), timestamps, call duration, and call resolution statuses.</li>
              <li><strong>Conversational Transcripts:</strong> Audio transcripts generated during live calls, subject to configurable automated retention schedules (default 30-day purge).</li>
              <li><strong>Call Recordings &amp; Consent Evidence:</strong> Where the tenant enables recording, audio is recorded via Amazon Connect (recordings land in the Connect instance S3 bucket) together with IVR consent evidence stored against the call record.</li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">3. Lawful Bases (UK GDPR Article 6)</h2>
            <p>
              We process personal data on the following bases: <strong>contract</strong> (providing the telephony service to the Customer); <strong>legitimate interests</strong> (service operation, security, and billing); <strong>legal obligation</strong> (tax and invoicing records); and <strong>consent</strong> (call recording, captured via IVR disclosure before recording begins). Controllers relying on Voxflow remain responsible for establishing their own lawful basis for directing caller data to the service.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">4. Data Retention &amp; Automated Purge Policy</h2>
            <p>
              Voxflow enforces automated data lifecycle policies with per-tenant configurable windows. Defaults: call transcripts 30 days, call records 90 days, and call recordings per tenant setting (recordings are off by default and retained only where the tenant enables them). Expired transcripts and recording pointers are permanently erased by automated purge jobs, and caller PII is scrubbed in line with customer-configured retention limits.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">5. Data Subject Rights (DSAR &amp; Right to Erasure)</h2>
            <p>
              In accordance with UK GDPR Chapter 3, individuals have the right to request:
            </p>
            <ul className="list-disc list-inside space-y-1 text-white/60 ml-2">
              <li><strong>Right of Access (DSAR Export):</strong> Complete JSON bundle of all stored interactions associated with a phone number or email address.</li>
              <li><strong>Right to be Forgotten (Erasure):</strong> Permanent anonymization and redaction of caller PII while preserving non-PII financial and inventory records.</li>
              <li><strong>Rectification, Restriction &amp; Objection:</strong> Correction of inaccurate data, restriction of processing, and objection to processing based on legitimate interests.</li>
            </ul>
            <p>
              To exercise any of these rights, email <a href="mailto:privacy@voxflow.cc" className="text-[#5EEAD4] hover:underline">privacy@voxflow.cc</a>. Requests are tracked in our privacy-requests ledger and answered within one month as UK GDPR requires. Where the request concerns caller data held on a Customer&apos;s behalf, we will redirect or coordinate with the relevant Controller.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">6. Sub-Processors &amp; Data Hosting</h2>
            <p>
              Voxflow runs on the following infrastructure — and nothing else. Project data and authentication identities live in Supabase Postgres (free tier). The application (FastAPI + Next.js) is hosted on an Oracle Cloud Always-Free virtual machine via Docker Compose behind Caddy with Let&apos;s Encrypt TLS. Conversational inference is transient: Groq hosted LLM and Whisper STT process call content in flight and do not retain it. Telephony ingress is Amazon Connect with Amazon Lex speech capture; call recordings land in the Connect instance S3 bucket. Billing is Stripe. Google Sheets acts as an optional per-tenant call-log mirror only, never the source of truth. We do not use AWS RDS, customer-managed KMS keys, or a secrets-management service, and we hold no ISO 27001 or SOC 2 certification — no such certification is claimed.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">7. Call Recording Disclosure</h2>
            <p>
              Every call carries a recording disclosure: callers are told the call may be recorded before any recording starts, and their IVR consent response is stored as consent evidence against the call record. If a caller does not consent, recording stays off for that call.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">8. Data Protection Officer (DPO)</h2>
            <p>
              To exercise data subject rights or submit privacy queries, email our Data Protection Officer at <a href="mailto:privacy@voxflow.cc" className="text-[#5EEAD4] hover:underline">privacy@voxflow.cc</a>.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">9. Cookies &amp; Site Tracking</h2>
            <p>
              The marketing site and dashboard use strictly-necessary cookies only: Supabase authentication session cookies that keep you signed in. We run no advertising trackers, no cross-site analytics, and no third-party marketing pixels. First-party product analytics (PostHog) runs only when configured, stores state in localStorage rather than cookies, never captures IP addresses, and sends only allow-listed non-identifying event properties. If a future release adds any non-essential cookie (for example product analytics), it will be off by default and gated behind an explicit consent banner — no non-essential cookie is ever set before you opt in. The banner implementation itself ships in a later release; this section is the policy it will enforce.
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
