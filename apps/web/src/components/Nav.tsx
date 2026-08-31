"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";

export default function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const isDashboard = pathname.startsWith("/dashboard");

  useEffect(() => {
    const onScroll = () => {
      setScrolled(window.scrollY > 40);
    };
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (isDashboard) return null;

  return (
    <header className="fixed top-0 left-0 right-0 z-50 transition-all duration-500" id="site-header">
      <div
        className={`backdrop-blur-xl border-b transition-all duration-500 ${
          scrolled ? "bg-[#050508]/80 border-white/[0.08] shadow-[0_4px_30px_rgba(0,0,0,0.6)]" : "bg-transparent border-white/[0.04]"
        }`}
        id="header-inner"
      >
        <div className="flex justify-between items-center w-full px-4 sm:px-6 lg:px-8 py-3 sm:py-4 max-w-7xl mx-auto">
          <Link href="/" className="flex items-center gap-2.5 z-10 group">
            <div className="relative w-8 h-8 rounded-lg bg-[#00ffcc]/10 border border-[#00ffcc]/30 flex items-center justify-center transition-all group-hover:border-[#00ffcc]/60 group-hover:shadow-[0_0_15px_rgba(0,255,204,0.25)]">
              <span
                className="material-symbols-outlined text-[#00ffcc] text-xl font-bold"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                graphic_eq
              </span>
            </div>
            <span className="text-xl sm:text-2xl font-headline font-black tracking-tight text-[#f8fafc]">
              VoxFlow
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-8" aria-label="Main navigation">
            <Link
              className="text-[#94a3b8] hover:text-[#00ffcc] transition-colors duration-300 font-label text-sm font-medium"
              href="/#platform"
            >
              Platform
            </Link>
            <Link
              className="text-[#94a3b8] hover:text-[#00ffcc] transition-colors duration-300 font-label text-sm font-medium"
              href="/#solutions"
            >
              Solutions
            </Link>
            <Link
              className="text-[#94a3b8] hover:text-[#00ffcc] transition-colors duration-300 font-label text-sm font-medium"
              href="/pricing"
            >
              Pricing
            </Link>
            <Link
              className="text-[#94a3b8] hover:text-[#00ffcc] transition-colors duration-300 font-label text-sm font-medium"
              href="/about"
            >
              About
            </Link>
          </nav>

          <div className="flex items-center gap-3.5 z-10">
            <Link
              href="/sign-in"
              className="hidden sm:inline-flex text-[#94a3b8] hover:text-[#f8fafc] transition-all font-label text-sm font-medium"
            >
              Sign In
            </Link>
            <Link
              href="/sign-up"
              className="bg-[#00ffcc] text-[#050508] px-5 sm:px-6 py-2 font-headline font-bold rounded-xl hover:shadow-[0_0_20px_rgba(0,255,204,0.4)] hover:bg-[#00ffcc]/90 transition-all active:scale-95 duration-150 text-sm"
            >
              Get Started
            </Link>
            <button
              onClick={() => setOpen(!open)}
              className="md:hidden flex items-center justify-center w-10 h-10 rounded-lg text-[#f8fafc] hover:bg-white/[0.05] transition-colors"
              aria-label="Toggle menu"
            >
              <span className="material-symbols-outlined text-2xl">
                {open ? "close" : "menu"}
              </span>
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {open && (
        <div className="fixed inset-0 z-40 bg-background/95 backdrop-blur-xl md:hidden flex flex-col items-center justify-center gap-8 text-lg">
          <Link
            className="text-primary font-bold font-label text-xl"
            href="/#platform"
            onClick={() => setOpen(false)}
          >
            Platform
          </Link>
          <Link
            className="text-on-surface-variant hover:text-primary transition-colors font-label text-xl"
            href="/#solutions"
            onClick={() => setOpen(false)}
          >
            Solutions
          </Link>
          <Link
            className="text-on-surface-variant hover:text-primary transition-colors font-label text-xl"
            href="/pricing"
            onClick={() => setOpen(false)}
          >
            Pricing
          </Link>
          <Link
            className="text-on-surface-variant hover:text-primary transition-colors font-label text-xl"
            href="/about"
            onClick={() => setOpen(false)}
          >
            About
          </Link>
          <hr className="w-16 border-outline-variant/30 my-2" />
          <Link
            href="/sign-in"
            onClick={() => setOpen(false)}
            className="text-on-surface-variant font-label"
          >
            Sign In
          </Link>
          <Link
            href="/sign-up"
            onClick={() => setOpen(false)}
            className="bg-primary text-on-primary px-8 py-3 font-headline font-bold rounded-xl"
          >
            Get Started
          </Link>
        </div>
      )}
    </header>
  );
}
