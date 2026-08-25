"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { FadeUp } from "@/components/ScrollAnimations";
import TurnstileWidget, { turnstileEnabled } from "@/components/TurnstileWidget";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function SignUpPage() {
  const { signUp, signIn, loading: authLoading } = useAuth();
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [company, setCompany] = useState("");
  const [password, setPassword] = useState("");
  const [language, setLanguage] = useState<"en" | "hi">("en");
  const [loading, setLoading] = useState(false);
  const [signUpError, setSignUpError] = useState("");
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const [turnstileReset, setTurnstileReset] = useState(0);

  const handleSignUp = async (event: React.FormEvent) => {
    event.preventDefault();
    setSignUpError("");

    if (!company.trim()) {
      setSignUpError("Please enter your company or workspace name.");
      return;
    }
    if (password.length < 6) {
      setSignUpError("Password must be at least 6 characters long.");
      return;
    }

    if (turnstileEnabled() && !turnstileToken) {
      setSignUpError("Please complete the security challenge before continuing.");
      return;
    }

    setLoading(true);

    try {
      // 1. Attempt Supabase Auth user registration (non-blocking if external auth is offline)
      await signUp(email.trim(), password.trim(), {
        name: name.trim(),
        company_name: company.trim(),
      }).catch((e) => {
        console.warn("Supabase auth warning:", e);
      });

      // 2. Call backend self-serve signup provisioning endpoint
      const provisionRes = await api.signupTenant({
        company_name: company.trim(),
        email: email.trim().toLowerCase(),
        name: name.trim(),
        default_language: language,
        seed_starter_data: true,
        turnstile_token: turnstileToken,
      });

      if (!provisionRes.ok || !provisionRes.tenant_id) {
        setSignUpError("Workspace provisioning encountered an issue. Please try again.");
        setLoading(false);
        return;
      }

      // 3. Set active tenant in storage & cookie
      if (typeof window !== "undefined") {
        localStorage.setItem("voxflow_active_tenant", provisionRes.tenant_id);
        localStorage.setItem("voxflow_demo_tenant", provisionRes.tenant_id);
        document.cookie = `auth-token=demo-user-${provisionRes.tenant_id}; path=/; max-age=86400`;
        localStorage.setItem(
          "voxflow_onboarding_data",
          JSON.stringify({
            tenantId: provisionRes.tenant_id,
            companyName: provisionRes.name,
            agentName: provisionRes.agent_name,
            language: provisionRes.default_language,
            stats: provisionRes.stats,
          })
        );
      }

      // 4. Ensure sign-in state & forward to onboarding wizard
      await signIn(email.trim(), password.trim()).catch(() => {});
      router.push("/onboarding");
    } catch (err: any) {
      console.error("Signup error:", err);
      setSignUpError(err?.message || "Failed to create workspace. Please check your details.");
      setLoading(false);
      if (turnstileEnabled()) setTurnstileReset((v) => v + 1);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 sm:px-6 pt-[5.5rem] pb-20 bg-[#0a0a12] grid-bg relative overflow-hidden">
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-96 h-96 bg-[#00ffcc]/10 blur-[120px] rounded-full pointer-events-none" />
      <FadeUp className="w-full max-w-lg relative z-10">
        <div className="glass neon-border rounded-2xl p-8 sm:p-10 border border-[#ff2d78]/30 shadow-[0_0_50px_rgba(0,0,0,0.5)]">
          <div className="text-center mb-8">
            <div className="h-12 w-12 rounded-xl bg-[#ff2d78] grid place-items-center font-headline font-extrabold text-[#1a0010] text-xl mx-auto mb-4 shadow-[0_0_20px_rgba(255,45,120,0.5)]">
              V
            </div>
            <h1 className="font-headline font-bold text-2xl sm:text-3xl text-[#e8e0f0]">
              Create Your Voice Workspace
            </h1>
            <p className="text-sm text-[#a098b0] mt-2 font-body">
              Self-serve onboarding — deploy your dedicated AI voice agent in 60 seconds.
            </p>
          </div>

          <form className="space-y-4" onSubmit={handleSignUp}>
            <Field
              label="Full Name"
              id="name"
              value={name}
              onChange={setName}
              placeholder="e.g. John Doe"
              type="text"
            />
            <Field
              label="Work Email"
              id="email"
              value={email}
              onChange={setEmail}
              placeholder="name@company.co.uk"
              type="email"
            />
            <Field
              label="Password"
              id="password"
              value={password}
              onChange={setPassword}
              placeholder="••••••••"
              type="password"
            />
            <Field
              label="Company / Business Name"
              id="company"
              value={company}
              onChange={setCompany}
              placeholder="e.g. Apex Logistics UK Ltd"
              type="text"
            />

            <div>
              <label className="text-xs font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                Primary Agent Language
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setLanguage("en")}
                  className={`py-2.5 px-3 rounded-xl text-xs font-medium border transition-all flex items-center justify-center gap-2 ${
                    language === "en"
                      ? "border-[#00ffcc] bg-[#00ffcc]/15 text-[#00ffcc] shadow-[0_0_15px_rgba(0,255,204,0.3)]"
                      : "border-[#302840]/60 bg-[#141422] text-[#a098b0] hover:text-[#e8e0f0]"
                  }`}
                >
                  <span>🇬🇧</span> UK English (en)
                </button>
                <button
                  type="button"
                  onClick={() => setLanguage("hi")}
                  className={`py-2.5 px-3 rounded-xl text-xs font-medium border transition-all flex items-center justify-center gap-2 ${
                    language === "hi"
                      ? "border-[#ff2d78] bg-[#ff2d78]/15 text-[#ff2d78] shadow-[0_0_15px_rgba(255,45,120,0.3)]"
                      : "border-[#302840]/60 bg-[#141422] text-[#a098b0] hover:text-[#e8e0f0]"
                  }`}
                >
                  <span>🇮🇳</span> Hindi (hi)
                </button>
              </div>
            </div>

            {turnstileEnabled() && (
              <TurnstileWidget action="sign_up" onToken={setTurnstileToken} resetCounter={turnstileReset} />
            )}

            {signUpError && (
              <div className="text-xs text-[#ff2d78] bg-[#ff2d78]/10 border border-[#ff2d78]/30 rounded-md p-2.5">
                {signUpError}
              </div>
            )}

            <button
              type="submit"
              disabled={loading || authLoading}
              className="w-full py-3.5 rounded-xl bg-[#ff2d78] text-[#1a0010] font-headline font-bold text-sm hover:shadow-[0_0_25px_rgba(255,45,120,0.5)] transition-all duration-200 active:scale-95 mt-2 disabled:opacity-50"
            >
              {loading || authLoading ? "Provisioning Workspace…" : "Launch My Workspace →"}
            </button>
          </form>

          <p className="text-center text-xs font-label text-[#a098b0] mt-6">
            Already have a workspace?{" "}
            <Link href="/sign-in" className="text-[#00ffcc] hover:text-[#00ffcc]/80 transition-colors font-bold">
              Sign In
            </Link>
          </p>
        </div>
      </FadeUp>
    </div>
  );
}

function Field({
  label,
  id,
  value,
  onChange,
  placeholder,
  type,
}: {
  label: string;
  id: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  type: string;
}) {
  return (
    <div>
      <label htmlFor={id} className="text-xs font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
        {label}
      </label>
      <input
        id={id}
        type={type}
        required
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="w-full px-4 py-3 rounded-xl bg-[#141422] border border-[#302840]/60 text-[#e8e0f0] text-sm placeholder:text-[#a098b0]/40 focus:outline-none focus:border-[#ff2d78] focus:ring-1 focus:ring-[#ff2d78]/40 transition-all font-body"
      />
    </div>
  );
}

