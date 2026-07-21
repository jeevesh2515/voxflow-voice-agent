"use client";
import Link from "next/link";
import { FadeUp } from "@/components/ScrollAnimations";

export default function SignInPage() {
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

          <form className="space-y-5" onSubmit={(e) => e.preventDefault()}>
            <div>
              <label htmlFor="email" className="text-xs font-label uppercase tracking-widest text-[#e8e0f0] block mb-2">Work Email</label>
              <input
                id="email"
                type="email"
                placeholder="name@company.com"
                className="w-full px-4 py-3 rounded-xl bg-[#141422] border border-[#302840]/60 text-[#e8e0f0] text-sm placeholder:text-[#a098b0]/40 focus:outline-none focus:border-[#ff2d78] focus:ring-1 focus:ring-[#ff2d78]/40 transition-all font-body"
              />
            </div>
            <div>
              <div className="flex justify-between items-center mb-2">
                <label htmlFor="password" className="text-xs font-label uppercase tracking-widest text-[#e8e0f0] block">Password</label>
                <a href="#" className="text-xs font-label text-[#00ffcc] hover:underline">Forgot?</a>
              </div>
              <input
                id="password"
                type="password"
                placeholder="••••••••"
                className="w-full px-4 py-3 rounded-xl bg-[#141422] border border-[#302840]/60 text-[#e8e0f0] text-sm placeholder:text-[#a098b0]/40 focus:outline-none focus:border-[#ff2d78] focus:ring-1 focus:ring-[#ff2d78]/40 transition-all font-body"
              />
            </div>
            <button
              type="submit"
              className="w-full py-3.5 rounded-xl bg-[#ff2d78] text-[#1a0010] font-headline font-bold text-sm hover:shadow-[0_0_25px_rgba(255,45,120,0.5)] transition-all duration-200 active:scale-95 mt-2"
            >
              Sign In to Operations
            </button>
          </form>

          <p className="text-center text-xs font-label text-[#a098b0] mt-8">
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
