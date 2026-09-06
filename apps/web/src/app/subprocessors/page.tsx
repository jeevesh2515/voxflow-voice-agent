import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Subprocessors | Voxflow Voice Agent",
  description: "Third-party subprocessors engaged by Voxflow, with purpose and data location.",
};

const PROCESSORS: Array<{
  name: string;
  purpose: string;
  data: string;
  location: string;
}> = [
  {
    name: "Supabase",
    purpose: "Primary database (Postgres) and authentication identity tokens",
    data: "Call records, transcripts metadata, tenant ledgers, auth identities",
    location: "EU region",
  },
  {
    name: "Amazon Web Services (Connect + Lex + S3)",
    purpose: "Telephony ingress, speech capture, call-recording storage",
    data: "Call audio recordings, contact-flow metadata, consent evidence",
    location: "eu-west-2 (London)",
  },
  {
    name: "Groq",
    purpose: "Transient LLM inference and hosted Whisper speech-to-text",
    data: "Call content in flight — processed, not retained",
    location: "To be confirmed — see DPA",
  },
  {
    name: "Stripe Payments UK Ltd",
    purpose: "Subscription billing and metered usage",
    data: "Billing identity, payment status, usage minutes",
    location: "UK / EU",
  },
  {
    name: "Google Sheets (optional)",
    purpose: "Per-tenant call-log mirror only, never the source of truth",
    data: "Call outcome rows for tenants that enable mirroring",
    location: "Customer's Google account region",
  },
];

export default function SubprocessorsPage() {
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
            UK GDPR Article 28
          </span>
          <h1 className="text-3xl sm:text-4xl font-headline font-extrabold text-white mt-4 tracking-tight">
            Subprocessors
          </h1>
          <p className="text-white/50 text-xs font-mono mt-2">Stable URL: /subprocessors • Last reviewed: September 2026</p>
        </div>

        <div className="mb-8 rounded-lg border border-[#5EEAD4]/30 bg-[#5EEAD4]/10 px-4 py-3 text-sm text-white/80">
          <p>
            <strong className="font-bold text-white">Template notice:</strong> This list is maintained alongside the Privacy Policy and DPA template. It is pending solicitor review and must not be relied on for real contracts or payments.
          </p>
        </div>

        <p className="text-white/70 leading-relaxed text-sm sm:text-base font-sans mb-8">
          Voxflow engages the following third parties to process personal data on behalf of our customers.
          We notify customers of any change to this list before it takes effect, per the DPA change-notice clause.
          Anything not listed here does not touch customer data.
        </p>

        <div className="space-y-4">
          {PROCESSORS.map((p) => (
            <div key={p.name} className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5">
              <h2 className="text-base font-headline font-bold text-white">{p.name}</h2>
              <dl className="mt-3 text-xs font-mono text-white/60 space-y-1">
                <div className="flex gap-2"><dt className="shrink-0">purpose:</dt><dd className="text-white/80">{p.purpose}</dd></div>
                <div className="flex gap-2"><dt className="shrink-0">data:</dt><dd className="text-white/80">{p.data}</dd></div>
                <div className="flex gap-2"><dt className="shrink-0">location:</dt><dd className="text-white/80">{p.location}</dd></div>
              </dl>
            </div>
          ))}
        </div>

        <p className="mt-8 text-white/50 text-xs font-mono">
          Questions: <Link href="/privacy" className="text-[#5EEAD4] hover:underline">Privacy Policy</Link> • Full processor terms in the DPA template (available on request).
        </p>
      </main>
    </div>
  );
}
