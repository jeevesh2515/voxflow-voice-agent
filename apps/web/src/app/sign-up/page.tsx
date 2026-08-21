"use client";

import Link from "next/link";
import { useState } from "react";
import { FadeUp } from "@/components/ScrollAnimations";
import TurnstileWidget, { turnstileEnabled } from "@/components/TurnstileWidget";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function SignUpPage() {
  const { signUp, loading: authLoading } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [signUpError, setSignUpError] = useState("");
  const [requested, setRequested] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const [turnstileReset, setTurnstileReset] = useState(0);

  const handleSignUp = async (event: React.FormEvent) => {
    event.preventDefault();
    setSignUpError("");
    if (turnstileEnabled()) {
      if (!turnstileToken) {
        setSignUpError("Please complete the verification challenge before requesting access.");
        return;
      }
      try {
        await api.verifyTurnstile(turnstileToken, "sign_up");
      } catch {
        setSignUpError("Verification could not be confirmed. Please try the challenge again.");
        setTurnstileReset((value) => value + 1);
        return;
      }
    }

    setLoading(true);
    const result = await signUp(email.trim(), password.trim(), {
      name: name.trim(),
      company_name: company.trim(),
      access_request: "design_partner_review_required",
    });
    if (result.error) {
      setSignUpError(result.error);
      setLoading(false);
      if (turnstileEnabled()) setTurnstileReset((value) => value + 1);
      return;
    }
    setRequested(true);
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 sm:px-6 pt-[5.5rem] pb-20 bg-[#0a0a12] grid-bg relative overflow-hidden">
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-96 h-96 bg-[#00ffcc]/10 blur-[120px] rounded-full pointer-events-none" />
      <FadeUp className="w-full max-w-lg relative z-10">
        <div className="glass neon-border rounded-2xl p-8 sm:p-10 border border-[#ff2d78]/30 shadow-[0_0_50px_rgba(0,0,0,0.5)]">
          <div className="text-center mb-8">
            <div className="h-12 w-12 rounded-xl bg-[#ff2d78] grid place-items-center font-headline font-extrabold text-[#1a0010] text-xl mx-auto mb-4 shadow-[0_0_20px_rgba(255,45,120,0.5)]">V</div>
            <h1 className="font-headline font-bold text-2xl sm:text-3xl text-[#e8e0f0]">Request Design-Partner Access</h1>
            <p className="text-sm text-[#a098b0] mt-2 font-body">Create an account request for the free MVP evaluation. A workspace is never created by this form.</p>
          </div>

          {requested ? <div className="rounded-xl border border-[#00ffcc]/30 bg-[#00ffcc]/10 p-5 text-sm text-[#bfffee]"><strong>Account request received.</strong><p className="mt-2">If email confirmation is enabled, confirm your address first. A platform administrator must then create your tenant and grant a server-authorized membership. No worker, provider, campaign, callback, or outbound call was activated.</p><Link href="/sign-in" className="mt-4 inline-block font-bold text-[#00ffcc] hover:underline">Return to sign in</Link></div> : <form className="space-y-4" onSubmit={handleSignUp}>
            <div className="rounded-xl border border-[#ffe04a]/30 bg-[#ffe04a]/5 px-4 py-3 text-xs text-[#fef3c7]">This is a design-partner access request, not self-service workspace activation. Access is reviewed and granted through tenant membership controls.</div>
            <Field label="Full name" id="name" value={name} onChange={setName} placeholder="Sarah Chen" type="text" />
            <Field label="Work email" id="email" value={email} onChange={setEmail} placeholder="sarah@company.com" type="email" />
            <Field label="Password" id="password" value={password} onChange={setPassword} placeholder="••••••••" type="password" />
            <Field label="Company / operation name" id="company" value={company} onChange={setCompany} placeholder="Example Operations" type="text" />
            {turnstileEnabled() && <TurnstileWidget action="sign_up" onToken={setTurnstileToken} resetCounter={turnstileReset} />}
            {signUpError && <div className="text-xs text-[#ff2d78] bg-[#ff2d78]/10 border border-[#ff2d78]/30 rounded-md p-2">{signUpError}</div>}
            <button type="submit" disabled={loading || authLoading} className="w-full py-3.5 rounded-xl bg-[#ff2d78] text-[#1a0010] font-headline font-bold text-sm hover:shadow-[0_0_25px_rgba(255,45,120,0.5)] transition-all duration-200 active:scale-95 mt-2 disabled:opacity-50">{(loading || authLoading) ? "Submitting Request…" : "Request Access Review"}</button>
          </form>}
          <p className="text-center text-xs font-label text-[#a098b0] mt-6">Already have a workspace? <Link href="/sign-in" className="text-[#00ffcc] hover:text-[#00ffcc]/80 transition-colors font-bold">Sign In</Link></p>
        </div>
      </FadeUp>
    </div>
  );
}

function Field({ label, id, value, onChange, placeholder, type }: { label: string; id: string; value: string; onChange: (value: string) => void; placeholder: string; type: string }) {
  return <div><label htmlFor={id} className="text-xs font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">{label}</label><input id={id} type={type} required value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="w-full px-4 py-3 rounded-xl bg-[#141422] border border-[#302840]/60 text-[#e8e0f0] text-sm placeholder:text-[#a098b0]/40 focus:outline-none focus:border-[#ff2d78] focus:ring-1 focus:ring-[#ff2d78]/40 transition-all font-body" /></div>;
}
