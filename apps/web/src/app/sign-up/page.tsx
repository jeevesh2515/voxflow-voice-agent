"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { FadeUp } from "@/components/ScrollAnimations";
import TurnstileWidget, { turnstileEnabled } from "@/components/TurnstileWidget";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

function SignUpForm() {
  const { signUp, signIn, loading: authLoading } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedPlan = (searchParams.get("plan") as any) || "starter";

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
      // 1. Register with Supabase Auth
      const authResult = await signUp(email.trim(), password.trim(), {
        name: name.trim(),
        company_name: company.trim(),
      });

      if (authResult.error) {
        setSignUpError(authResult.error);
        setLoading(false);
        if (turnstileEnabled()) setTurnstileReset((v) => v + 1);
        return;
      }

      if (!authResult.hasSession) {
        const signInResult = await signIn(email.trim(), password.trim());
        if (signInResult.error) {
          setSignUpError(
            "Your account was created, but we couldn't start a session automatically. " +
              "Please check your email to confirm your address, then sign in to launch your workspace."
          );
          setLoading(false);
          return;
        }
      }

      // 2. Call backend self-serve signup provisioning endpoint with pre-selected plan
      const provisionRes = await api.signupTenant({
        company_name: company.trim(),
        email: email.trim().toLowerCase(),
        name: name.trim(),
        default_language: language,
        plan: requestedPlan,
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
    <div className="min-h-screen bg-[#080810] flex items-center justify-center p-4 selection:bg-[#ff2d78]/30 selection:text-[#ff2d78]">
      <FadeUp>
        <div className="w-full max-w-md bg-[#0e0e1a]/80 backdrop-blur-xl border border-[#302840]/60 rounded-3xl p-8 shadow-2xl relative overflow-hidden">
          <div className="text-center mb-8">
            <Link href="/" className="inline-block font-headline font-black text-2xl tracking-wider text-[#e8e0f0] mb-2 hover:text-[#00ffcc] transition-colors">
              VOX<span className="text-[#ff2d78]">FLOW</span>
            </Link>
            <h1 className="text-xl font-headline font-bold text-[#e8e0f0]">Start Your 14-Day Free Trial</h1>
            <p className="text-xs font-label text-[#a098b0] mt-1">
              Selected Tier: <span className="font-bold text-teal-400 capitalize">{requestedPlan}</span> • Ready in ~30 seconds
            </p>
          </div>

          <form onSubmit={handleSignUp} className="space-y-4">
            <Field
              label="Your Name"
              id="name"
              type="text"
              placeholder="Anita Desai"
              value={name}
              onChange={setName}
            />

            <Field
              label="Work Email"
              id="email"
              type="email"
              placeholder="anita@varunbeverages.com"
              value={email}
              onChange={setEmail}
            />

            <Field
              label="Company / Workspace Name"
              id="company"
              type="text"
              placeholder="Varun Beverages Ltd"
              value={company}
              onChange={setCompany}
            />

            <Field
              label="Password"
              id="password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={setPassword}
            />

            <div>
              <label htmlFor="language" className="text-xs font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                Primary Agent Language
              </label>
              <select
                id="language"
                value={language}
                onChange={(e) => setLanguage(e.target.value as "en" | "hi")}
                className="w-full px-4 py-3 rounded-xl bg-[#141422] border border-[#302840]/60 text-[#e8e0f0] text-sm focus:outline-none focus:border-[#ff2d78] transition-all font-body"
              >
                <option value="en">English (UK / Global)</option>
                <option value="hi">Hindi (हिन्दी)</option>
              </select>
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

export default function SignUpPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#080810] flex items-center justify-center text-white">Loading...</div>}>
      <SignUpForm />
    </Suspense>
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
