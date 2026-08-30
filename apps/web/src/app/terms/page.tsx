import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Terms of Service | VoxFlow Voice Agent",
  description: "Terms and conditions governing the use of the VoxFlow Voice AI enterprise platform.",
};

export default function TermsOfServicePage() {
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
            Legal & Terms
          </span>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white mt-4 tracking-tight">
            Terms of Service
          </h1>
          <p className="text-slate-400 text-sm mt-2">Last Updated: August 30, 2026 • Governing Law: England & Wales</p>
        </div>

        <div className="space-y-10 text-slate-300 leading-relaxed text-sm sm:text-base">
          <section className="space-y-3">
            <h2 className="text-xl font-bold text-white tracking-tight">1. Agreement to Terms</h2>
            <p>
              These Terms of Service (&quot;Terms&quot;) constitute a legally binding agreement between VoxFlow Technologies Ltd (&quot;VoxFlow&quot;, &quot;we&quot;, &quot;us&quot;, or &quot;our&quot;) and the organization or individual accessing or using the VoxFlow enterprise voice AI platform (&quot;Customer&quot;, &quot;you&quot;).
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-bold text-white tracking-tight">2. Description of Service</h2>
            <p>
              VoxFlow provides automated, conversational voice AI telephony systems for enterprise call handling, order inquiries, supplier verification, appointment scheduling, and automated data synchronization (including Google Sheets and webhook integrations).
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-bold text-white tracking-tight">3. Subscriptions, Invoicing & Stripe Billing</h2>
            <p>
              VoxFlow services are provided on a subscription basis (Starter, Growth, Enterprise). Subscriptions are billed in advance in GBP (£) or USD ($) on a recurring monthly or annual basis via Stripe.
            </p>
            <ul className="list-disc list-inside space-y-1 text-slate-400 ml-2">
              <li><strong>Free Trials:</strong> 14-day free trial periods grant full platform access without immediate charge.</li>
              <li><strong>Failed Payments:</strong> If payment fails, an automated grace period applies before telephony services transition to inactive.</li>
              <li><strong>VAT & Invoicing:</strong> Invoices with compliant UK VAT receipts are delivered via the Stripe Customer Portal.</li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-bold text-white tracking-tight">4. Tenant Data Isolation & Security</h2>
            <p>
              Each tenant workspace operates in cryptographic isolation. VoxFlow enforces zero cross-tenant data leakage, 3-tier Role-Based Access Control (Owner, Operator, Viewer), and data residency compliance in our UK/EU data centers.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-bold text-white tracking-tight">5. Telephony Compliance & Acceptable Use</h2>
            <p>
              Customers must not use the VoxFlow voice platform for unlawful robocalling, deceptive impersonation, harassment, or in violation of Ofcom / FCC telephony regulations.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-bold text-white tracking-tight">6. Limitation of Liability</h2>
            <p>
              To the maximum extent permitted by UK law, VoxFlow shall not be liable for indirect, incidental, special, or consequential damages resulting from downtime, network outages, or third-party telephony provider carrier failures.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-bold text-white tracking-tight">7. Contact Information</h2>
            <p>
              For legal inquiries or corporate contracts, contact our team at <a href="mailto:legal@voxflow.ai" className="text-teal-400 hover:underline">legal@voxflow.ai</a>.
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
