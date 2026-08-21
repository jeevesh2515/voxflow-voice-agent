"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { FadeUp } from "@/components/ScrollAnimations";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import TurnstileWidget, { turnstileEnabled } from "@/components/TurnstileWidget";

export default function SignInPage() {
  const router = useRouter();
  const { signIn, demoSignIn, loading: authLoading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [signInError, setSignInError] = useState("");
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const [turnstileReset, setTurnstileReset] = useState(0);

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setSignInError("");
    if (!email.trim()) { setSignInError("Email is required"); return; }
    if (!password.trim()) { setSignInError("Password is required"); return; }
    if (turnstileEnabled()) {
      if (!turnstileToken) {
        setSignInError("Please complete the verification challenge before signing in.");
        return;
      }
      try {
        await api.verifyTurnstile(turnstileToken, "sign_in");
      } catch {
        setSignInError("Verification could not be confirmed. Please try the challenge again.");
        setTurnstileReset((value) => value + 1);
        return;
      }
    }

    setLoading(true);
    const result = await signIn(email.trim(), password.trim());
    if (result.error) {
      setSignInError(result.error);
      setLoading(false);
      if (turnstileEnabled()) setTurnstileReset((value) => value + 1);
      return;
    }

    router.push("/dashboard");
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 sm:px-6 pt-[5.5rem] pb-20 bg-[#0a0a12] grid-bg relative overflow-hidden">
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-96 h-96 bg-[#ff2d78]/10 blur-[120px] rounded-full pointer-events-none" />
      <FadeUp className="w-full max-w-md relative z-10">
        <div className="glass neon-border rounded-2xl p-8 sm:p-10 border border-[#ff2d78]/30 shadow-[0_0_50px_rgba(0,0,0,0.5)]">
          <div className="text-center mb-8">
            <div className="h-12 w-12 rounded-xl bg-[#ff2d78] grid place-items-center font-headline font-extrabold text-[#1a0010] text-xl mx-auto mb-4 shadow-[0_0_20px_rgba(255,45,120,0.5)]">
              V
            </div>
            <h1 className="font-headline font-bold text-2xl sm:text-3xl text-[#e8e0f0]">Welcome Back</h1>
            <p className="text-sm text-[#a098b0] mt-2 font-body">Sign in to manage your voice operations</p>
          </div>

          <form className="space-y-4" onSubmit={handleSignIn}>
            <div className="rounded-xl border border-[#302840]/60 bg-[#141422] px-4 py-3 text-xs text-[#a098b0]">
              Your workspaces are loaded from your server-authorized membership after sign-in. A company selector cannot grant access.
            </div>

            <div>
              <label htmlFor="email" className="text-xs font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">Work Email</label>
              <input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="name@company.com"
                className="w-full px-4 py-3 rounded-xl bg-[#141422] border border-[#302840]/60 text-[#e8e0f0] text-sm placeholder:text-[#a098b0]/40 focus:outline-none focus:border-[#ff2d78] focus:ring-1 focus:ring-[#ff2d78]/40 transition-all font-body"
              />
            </div>
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label htmlFor="password" className="text-xs font-label uppercase tracking-widest text-[#e8e0f0] block">Password</label>
                <span className="text-xs font-label text-[#a098b0] cursor-default" title="Password reset coming soon">Forgot?</span>
              </div>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full px-4 py-3 rounded-xl bg-[#141422] border border-[#302840]/60 text-[#e8e0f0] text-sm placeholder:text-[#a098b0]/40 focus:outline-none focus:border-[#ff2d78] focus:ring-1 focus:ring-[#ff2d78]/40 transition-all font-body"
              />
            </div>
            {turnstileEnabled() && <TurnstileWidget action="sign_in" onToken={setTurnstileToken} resetCounter={turnstileReset} />}
            {signInError && <div className="text-xs text-danger-500 bg-danger-500/10 border border-danger-500/30 rounded-md p-2">{signInError}</div>}
            <button
              type="submit"
              disabled={loading || authLoading}
              className="w-full py-3.5 rounded-xl bg-[#ff2d78] text-[#1a0010] font-headline font-bold text-sm hover:shadow-[0_0_25px_rgba(255,45,120,0.5)] transition-all duration-200 active:scale-95 mt-2 disabled:opacity-50"
            >
              {(loading || authLoading) ? "Authenticating..." : "Sign In to Operations"}
            </button>

            <div className="relative flex items-center justify-center my-3">
              <div className="border-t border-[#302840]/60 w-full" />
              <span className="bg-[#141422] px-3 text-[10px] font-label text-[#a098b0] uppercase tracking-wider">Or</span>
              <div className="border-t border-[#302840]/60 w-full" />
            </div>

            <button
              type="button"
              onClick={() => {
                demoSignIn("varun");
                router.push("/dashboard");
              }}
              className="w-full py-2.5 rounded-xl bg-[#1a1829] hover:bg-[#252038] border border-[#ff2d78]/40 text-[#e8e0f0] font-headline font-semibold text-xs flex items-center justify-center gap-2 hover:shadow-[0_0_20px_rgba(255,45,120,0.2)] transition-all duration-200"
            >
              <span>⚡</span> Open Read-Only Demo Workspace
            </button>
          </form>

          <p className="text-center text-xs font-label text-[#a098b0] mt-6">
            Don&apos;t have a workspace?{" "}
            <Link href="/sign-up" className="text-[#00ffcc] hover:text-[#00ffcc]/80 transition-colors font-bold">
              Request Pilot
            </Link>
          </p>
        </div>
      </FadeUp>
    </div>
  );
}
