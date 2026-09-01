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
  const [navCoords, setNavCoords] = useState<{ x: number; y: number; active: boolean }>({ x: 0, y: 0, active: false });
  const isDashboard = pathname.startsWith("/dashboard");

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 28);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const handleNavPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setNavCoords({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      active: true,
    });
  };

  const handleNavPointerLeave = () => {
    setNavCoords((prev) => ({ ...prev, active: false }));
  };

  if (isDashboard) return null;

  return (
    <header className="pointer-events-none fixed inset-x-0 top-0 z-50 px-3 pt-3 sm:px-5 sm:pt-5" id="site-header">
      <div
        onPointerMove={handleNavPointerMove}
        onPointerLeave={handleNavPointerLeave}
        className={`site-nav pointer-events-auto relative mx-auto flex max-w-6xl items-center justify-between overflow-hidden transition-all duration-300 ${
          scrolled ? "site-nav-scrolled" : ""
        }`}
        style={
          navCoords.active
            ? ({
                "--nav-x": `${navCoords.x}px`,
                "--nav-y": `${navCoords.y}px`,
              } as React.CSSProperties)
            : undefined
        }
      >
        {/* Terminal Industries Interactive Cursor Spotlight Beam */}
        <div
          className="nav-spotlight-beam absolute inset-0 pointer-events-none transition-opacity duration-300"
          style={{
            opacity: navCoords.active ? 1 : 0,
            background: `radial-gradient(130px circle at var(--nav-x, 50%) var(--nav-y, 50%), rgba(0, 255, 204, 0.16), rgba(255, 45, 120, 0.06) 45%, transparent 75%)`,
          }}
          aria-hidden="true"
        />
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
            <span className="cta-arrow-badge"><span className="material-symbols-outlined text-[15px]">arrow_outward</span></span>
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
