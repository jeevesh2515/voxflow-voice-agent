import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Service | Voxflow Voice Agent",
  description: "Terms and conditions governing the use of the Voxflow Voice AI enterprise platform.",
};

export default function TermsOfServicePage() {
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
            Legal &amp; Terms
          </span>
          <h1 className="text-3xl sm:text-4xl font-headline font-extrabold text-white mt-4 tracking-tight">
            Terms of Service
          </h1>
          <p className="text-white/50 text-xs font-mono mt-2">Last Updated: August 30, 2026 • Governing Law: England &amp; Wales</p>
        </div>

        <div className="space-y-10 text-white/70 leading-relaxed text-sm sm:text-base font-sans">
          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">1. Agreement to Terms</h2>
            <p>
              These Terms of Service (&quot;Terms&quot;) constitute a legally binding agreement between Voxflow Technologies Ltd (&quot;Voxflow&quot;, &quot;we&quot;, &quot;us&quot;, or &quot;our&quot;) and the organization or individual accessing or using the Voxflow enterprise voice AI platform (&quot;Customer&quot;, &quot;you&quot;).
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">2. Description of Service</h2>
            <p>
              Voxflow provides automated, conversational voice AI telephony systems for enterprise call handling, order inquiries, supplier verification, appointment scheduling, and automated data synchronization (including Google Sheets and webhook integrations).
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">3. Subscriptions, Invoicing &amp; Stripe Billing</h2>
            <p>
              Voxflow services are provided on a subscription basis (Starter, Growth, Enterprise). Subscriptions are billed in advance in GBP (£) or USD ($) on a recurring monthly or annual basis via Stripe.
            </p>
            <ul className="list-disc list-inside space-y-1 text-white/60 ml-2">
              <li><strong>Free Trials:</strong> 14-day free trial periods grant full platform access without immediate charge.</li>
              <li><strong>Failed Payments:</strong> If payment fails, an automated grace period applies before telephony services transition to inactive.</li>
              <li><strong>VAT &amp; Invoicing:</strong> Invoices with compliant UK VAT receipts are delivered via the Stripe Customer Portal.</li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">4. Tenant Data Isolation &amp; Security</h2>
            <p>
              Each tenant workspace operates in cryptographic isolation. Voxflow enforces zero cross-tenant data leakage, 3-tier Role-Based Access Control (Owner, Operator, Viewer), and data residency compliance in our UK/EU data centers.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">5. Telephony Compliance &amp; Acceptable Use</h2>
            <p>
              Customers must not use the Voxflow voice platform for unlawful robocalling, deceptive impersonation, harassment, or in violation of Ofcom / FCC telephony regulations.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">6. Limitation of Liability</h2>
            <p>
              To the maximum extent permitted by UK law, Voxflow shall not be liable for indirect, incidental, special, or consequential damages resulting from downtime, network outages, or third-party telephony provider carrier failures.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">7. Contact Information</h2>
            <p>
              For legal inquiries or corporate contracts, contact our team at <a href="mailto:legal@voxflow.ai" className="text-[#5EEAD4] hover:underline">legal@voxflow.ai</a>.
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
