import Link from "next/link";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "Refund & Cancellation Policy | Voxflow Voice Agent",
  description: "Subscription cancellation, free trial, and refund policies for Voxflow.",
};

export default function RefundPolicyPage() {
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
            Billing &amp; Subscriptions
          </span>
          <h1 className="text-3xl sm:text-4xl font-headline font-extrabold text-white mt-4 tracking-tight">
            Refund &amp; Cancellation Policy
          </h1>
          <p className="text-white/50 text-xs font-mono mt-2">Transparent, self-serve billing terms for Voxflow customers.</p>
        </div>

        <div className="space-y-10 text-white/70 leading-relaxed text-sm sm:text-base font-sans">
          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">1. 14-Day Risk-Free Trial</h2>
            <p>
              Every new Voxflow organization starts with a <strong>14-day free trial</strong>. You will not be charged during this period, and you can cancel anytime from your dashboard with zero penalty or hidden fees.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">2. Subscription Cancellation</h2>
            <p>
              You can cancel your subscription at any time directly through the <strong>Stripe Customer Portal</strong> accessible from your Voxflow Settings dashboard. Upon cancellation:
            </p>
            <ul className="list-disc list-inside space-y-1 text-white/60 ml-2">
              <li>Your service remains active through the end of your current paid billing period.</li>
              <li>No further recurring charges will be made.</li>
              <li>Your call records and settings remain available for export in accordance with your retention policy.</li>
            </ul>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">3. Refund Policy</h2>
            <p>
              Subscription fees for Starter and Growth plans are billed in advance and are non-refundable once the billing cycle commences, except where required by applicable UK consumer or commercial statutory regulations. If you experience an unexpected billing error or platform outage, please contact our support team within 14 days of the charge date for review and credit.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-xl font-headline font-bold text-white tracking-tight">4. Billing Disputes &amp; Support</h2>
            <p>
              If you have questions regarding an invoice or need billing assistance, reach out directly to our finance team at <a href="mailto:billing@voxflow.ai" className="text-[#5EEAD4] hover:underline">billing@voxflow.ai</a>.
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
