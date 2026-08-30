import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Refund & Cancellation Policy | VoxFlow Voice Agent",
  description: "Subscription cancellation, free trial, and refund policies for VoxFlow.",
};

export default function RefundPolicyPage() {
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
            Billing & Subscriptions
          </span>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white mt-4 tracking-tight">
            Refund & Cancellation Policy
          </h1>
          <p className="text-slate-400 text-sm mt-2">Transparent, self-serve billing terms for VoxFlow customers.</p>
        </div>

        <div className="space-y-10 text-slate-300 leading-relaxed text-sm sm:text-base">
          <section className="space-y-3">
            <h2 className="text-xl font-bold text-white tracking-tight">1. 14-Day Risk-Free Trial</h2>
            <p>
              Every new VoxFlow organization starts with a <strong>14-day free trial</strong>. You will not be charged during this period, and you can cancel anytime from your dashboard with zero penalty or hidden fees.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-bold text-white tracking-tight">2. Subscription Cancellation</h2>
            <p>
              You can cancel your subscription at any time directly through the <strong>Stripe Customer Portal</strong> accessible from your VoxFlow Settings dashboard. Upon cancellation:
            </p>
            <ul className="list-disc list-inside space-y-1 text-slate-400 ml-2">
              <li>Your service remains active through the end of your current paid billing period.</li>
              <li>No further recurring charges will be made.</li>
              <li>Your call records and settings remain available for export in accordance with your retention policy.</li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-bold text-white tracking-tight">3. Refund Policy</h2>
            <p>
              Subscription fees for Starter and Growth plans are billed in advance and are non-refundable once the billing cycle commences, except where required by applicable UK consumer or commercial statutory regulations. If you experience an unexpected billing error or platform outage, please contact our support team within 14 days of the charge date for review and credit.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-bold text-white tracking-tight">4. Billing Disputes & Support</h2>
            <p>
              If you have questions regarding an invoice or need billing assistance, reach out directly to our finance team at <a href="mailto:billing@voxflow.ai" className="text-teal-400 hover:underline">billing@voxflow.ai</a>.
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
