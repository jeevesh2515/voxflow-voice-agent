"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { FadeUp } from "@/components/ScrollAnimations";
import { useTenant } from "@/lib/tenant-context";

export default function SignInPage() {
  const router = useRouter();
  const { tenants, setActiveTenantId } = useTenant();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [selectedTenant, setSelectedTenant] = useState(tenants[0]?.id || "varun");
  const [loading, setLoading] = useState(false);
  const [signInError, setSignInError] = useState("");

  const handleSignIn = (e: React.FormEvent) => {
    e.preventDefault();
    setSignInError("");
    if (!email.trim()) { setSignInError("Email is required"); return; }
    if (!password.trim()) { setSignInError("Password is required"); return; }
    setLoading(true);

    setActiveTenantId(selectedTenant);
    localStorage.setItem(
      "voxflow_session",
      JSON.stringify({
        user: {
          name: email.split("@")[0],
          email: email,
          tenant_id: selectedTenant,
        },
        token: `auth-token-${Date.now()}`,
      })
    );

    setTimeout(() => {
      router.push("/dashboard");
    }, 400);
  };

  const handleQuickDemo = () => {
    setLoading(true);
    setActiveTenantId("varun");
    localStorage.setItem(
      "voxflow_session",
      JSON.stringify({
        user: {
          name: "Demo Admin",
          email: "demo@voxflow.ai",
          tenant_id: "varun",
        },
        token: "demo-token-12345",
      })
    );
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
            <div>
              <label htmlFor="tenant" className="text-xs font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                Select Company Workspace
              </label>
              <select
                id="tenant"
                value={selectedTenant}
                onChange={(e) => setSelectedTenant(e.target.value)}
                className="w-full px-4 py-3 rounded-xl bg-[#141422] border border-[#302840]/60 text-[#e8e0f0] text-sm focus:outline-none focus:border-[#ff2d78] transition-all font-body"
              >
                {tenants.map((t) => (
                  <option key={t.id} value={t.id} className="bg-[#141422] text-[#e8e0f0]">
                    {t.name} ({t.id})
                  </option>
                ))}
              </select>
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
            {signInError && <div className="text-xs text-danger-500 bg-danger-500/10 border border-danger-500/30 rounded-md p-2">{signInError}</div>}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 rounded-xl bg-[#ff2d78] text-[#1a0010] font-headline font-bold text-sm hover:shadow-[0_0_25px_rgba(255,45,120,0.5)] transition-all duration-200 active:scale-95 mt-2 disabled:opacity-50"
            >
              {loading ? "Authenticating..." : "Sign In to Operations"}
            </button>
          </form>

          <div className="mt-4 pt-4 border-t border-[#302840]/40 text-center">
            <button
              type="button"
              onClick={handleQuickDemo}
              className="w-full py-2.5 rounded-xl bg-[#1e1e30] border border-[#00ffcc]/30 text-[#00ffcc] font-label text-xs hover:bg-[#00ffcc]/10 transition-colors"
            >
              ⚡ Quick Demo 1-Click Login to Dashboard
            </button>
          </div>

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
