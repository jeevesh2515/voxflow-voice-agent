"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const links = [
  { label: "Product", href: "/#section-05" },
  { label: "Pricing", href: "/pricing" },
  { label: "Hear it", href: "/#section-04" },
  { label: "Contact", href: "/contact" },
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
        className={`site-nav pointer-events-auto relative mx-auto flex max-w-6xl items-center justify-between overflow-hidden transition-all duration-300 rounded-full border border-white/[0.08] bg-[#030308]/80 backdrop-blur-xl px-4 py-2.5 shadow-2xl ${
          scrolled ? "border-[#5EEAD4]/20 shadow-[0_0_25px_rgba(94,234,212,0.1)]" : ""
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
        {/* Spotlight Beam */}
        <div
          className="absolute inset-0 pointer-events-none transition-opacity duration-300"
          style={{
            opacity: navCoords.active ? 1 : 0,
            background: `radial-gradient(130px circle at var(--nav-x, 50%) var(--nav-y, 50%), rgba(94, 234, 212, 0.16), transparent 75%)`,
          }}
          aria-hidden="true"
        />

        <Link href="/" className="group relative z-10 flex items-center gap-2.5" aria-label="Voxflow home">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#5EEAD4]/10 border border-[#5EEAD4]/20 text-[#5EEAD4]" aria-hidden="true">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M2 10v4" />
              <path d="M6 6v12" />
              <path d="M10 3v18" />
              <path d="M14 8v8" />
              <path d="M18 5v14" />
              <path d="M22 10v4" />
            </svg>
          </span>
          <span className="font-headline text-lg font-black tracking-[-0.055em] text-white sm:text-xl">
            VOX<span className="text-[#5EEAD4]">FLOW</span>
          </span>
        </Link>

        <nav className="hidden items-center gap-1 lg:flex" aria-label="Main navigation">
          {links.map((link) => (
            <Link key={link.label} href={link.href} className="px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.12em] text-white/70 hover:text-white transition-colors font-mono">
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="relative z-10 flex items-center gap-2 sm:gap-3">
          <Link href="/sign-up" className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full min-h-[44px] bg-[#5EEAD4] text-[#030308] text-xs font-bold font-headline hover:shadow-[0_0_20px_rgba(94,234,212,0.45)] transition-all">
            Fix one workflow
            <span className="inline-flex items-center" aria-hidden="true">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="7" y1="17" x2="17" y2="7" />
                <polyline points="7 7 17 7 17 17" />
              </svg>
            </span>
          </Link>
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            className="flex h-8 w-8 items-center justify-center rounded-full border border-white/[0.09] text-white min-h-[44px] transition-colors hover:bg-white/[0.06] lg:hidden"
            aria-label="Toggle menu"
            aria-expanded={open}
          >
            {open ? (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <line x1="4" y1="12" x2="20" y2="12" />
                <line x1="4" y1="6" x2="20" y2="6" />
                <line x1="4" y1="18" x2="20" y2="18" />
              </svg>
            )}
          </button>
        </div>
      </div>

      {open && (
        <div className="pointer-events-auto absolute left-3 right-3 top-[calc(100%+0.5rem)] rounded-2xl border border-white/[0.1] bg-[#030308]/95 p-3 shadow-2xl backdrop-blur-2xl sm:left-5 sm:right-5 lg:hidden">
          <nav className="grid gap-1" aria-label="Mobile navigation">
            {links.map((link) => (
              <Link
                key={link.label}
                href={link.href}
                onClick={() => setOpen(false)}
                className="rounded-xl px-4 py-3 text-sm font-semibold text-white/80 transition-colors hover:bg-white/[0.06] hover:text-white font-mono"
              >
                {link.label}
              </Link>
            ))}
            <Link href="/sign-up" onClick={() => setOpen(false)} className="rounded-xl px-4 py-3 text-sm font-semibold text-[#5EEAD4] transition-colors hover:bg-white/[0.06] font-mono">
              Fix one workflow →
            </Link>
          </nav>
        </div>
      )}
    </header>
  );
}
