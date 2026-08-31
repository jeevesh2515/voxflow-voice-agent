"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const links = [
  { label: "Platform", href: "/#platform" },
  { label: "Intelligence", href: "/#solutions" },
  { label: "Economics", href: "/#roi" },
  { label: "Pricing", href: "/pricing" },
];

export default function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const isDashboard = pathname.startsWith("/dashboard");

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 28);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (isDashboard) return null;

  return (
    <header className="pointer-events-none fixed inset-x-0 top-0 z-50 px-3 pt-3 sm:px-5 sm:pt-5" id="site-header">
      <div className={`site-nav pointer-events-auto mx-auto flex max-w-6xl items-center justify-between ${scrolled ? "site-nav-scrolled" : ""}`}>
        <Link href="/" className="group relative z-10 flex items-center gap-2.5" aria-label="VoxFlow home">
          <span className="nav-mark flex h-8 w-8 items-center justify-center" aria-hidden="true">
            <span className="material-symbols-outlined text-[18px]">graphic_eq</span>
          </span>
          <span className="font-headline text-lg font-black tracking-[-0.055em] text-white sm:text-xl">VoxFlow</span>
        </Link>

        <nav className="hidden items-center gap-1 lg:flex" aria-label="Main navigation">
          {links.map((link) => (
            <Link key={link.label} href={link.href} className="nav-link px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.12em]">
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="relative z-10 flex items-center gap-2 sm:gap-3">
          <span className="nav-status hidden items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-[#a4b2bc] sm:flex">
            <span className="h-1.5 w-1.5 rounded-full bg-[#00ffcc]" />
            Systems live
          </span>
          <Link href="/sign-in" className="hidden px-2 text-xs font-semibold text-[#a4b2bc] transition-colors hover:text-white md:inline-flex">
            Sign in
          </Link>
          <Link href="/sign-up" className="nav-cta inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-bold sm:px-4">
            Get started
            <span className="material-symbols-outlined text-[15px]">arrow_outward</span>
          </Link>
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            className="flex h-8 w-8 items-center justify-center rounded-full border border-white/[0.09] text-white transition-colors hover:bg-white/[0.06] lg:hidden"
            aria-label="Toggle menu"
            aria-expanded={open}
          >
            <span className="material-symbols-outlined text-[19px]">{open ? "close" : "menu"}</span>
          </button>
        </div>
      </div>

      {open && (
        <div className="pointer-events-auto absolute left-3 right-3 top-[calc(100%+0.5rem)] rounded-2xl border border-white/[0.1] bg-[#08080d]/95 p-3 shadow-2xl backdrop-blur-2xl sm:left-5 sm:right-5 lg:hidden">
          <nav className="grid gap-1" aria-label="Mobile navigation">
            {links.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                onClick={() => setOpen(false)}
                className="rounded-xl px-4 py-3 text-sm font-semibold text-[#c4ced5] transition-colors hover:bg-white/[0.06] hover:text-white"
              >
                {link.label}
              </Link>
            ))}
            <Link href="/sign-in" onClick={() => setOpen(false)} className="rounded-xl px-4 py-3 text-sm font-semibold text-[#c4ced5] transition-colors hover:bg-white/[0.06] hover:text-white">
              Sign in
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}
