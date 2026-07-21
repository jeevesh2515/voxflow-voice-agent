"use client";
import Link from "next/link";
import { FadeUp } from "@/components/ScrollAnimations";

export default function SignUpPage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-6 pt-[5.5rem] pb-20">
      <FadeUp className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="h-10 w-10 rounded-xl bg-primary grid place-items-center font-bold text-primary-foreground mx-auto mb-4 shadow-glow">
            V
          </div>
          <h1 className="text-2xl font-bold text-foreground">Get Started</h1>
          <p className="text-sm text-muted-foreground mt-1">Create an account to get started</p>
        </div>

        <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
          <div>
            <label htmlFor="name" className="text-sm font-medium text-foreground/80 block mb-1.5">Name</label>
            <input
              id="name"
              type="text"
              placeholder="Your name"
              className="w-full px-4 py-2.5 rounded-lg bg-card border border-border text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all"
            />
          </div>
          <div>
            <label htmlFor="email" className="text-sm font-medium text-foreground/80 block mb-1.5">Email</label>
            <input
              id="email"
              type="email"
              placeholder="you@example.com"
              className="w-full px-4 py-2.5 rounded-lg bg-card border border-border text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all"
            />
          </div>
          <div>
            <label htmlFor="password" className="text-sm font-medium text-foreground/80 block mb-1.5">Password</label>
            <input
              id="password"
              type="password"
              placeholder="••••••••"
              className="w-full px-4 py-2.5 rounded-lg bg-card border border-border text-foreground text-sm placeholder:text-muted-foreground focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all"
            />
          </div>
          <button
            type="submit"
            className="w-full py-2.5 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-all duration-200"
          >
            Get Started
          </button>
        </form>

        <p className="text-center text-sm text-muted-foreground mt-6">
          Already have an account?{" "}
          <Link href="/sign-in" className="text-primary hover:text-primary/80 transition-colors font-medium">
            Sign In
          </Link>
        </p>
      </FadeUp>
    </div>
  );
}
