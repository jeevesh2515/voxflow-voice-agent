"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Menu, X } from "lucide-react";
import { useState, useEffect } from "react";

const links = [
  { href: "/#operations", label: "Operations" },
  { href: "/#how-it-works", label: "How it works" },
  { href: "/pricing", label: "Pricing" },
  { href: "/about", label: "About" },
];

export default function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const isDashboard = pathname.startsWith("/dashboard");

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  if (isDashboard) return null;

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 h-[4.5rem] transition-all duration-300 ${
        scrolled
          ? "bg-[#0f0f1a]/85 backdrop-blur-xl border-b border-[#302840]/40 shadow-lg"
          : "bg-transparent"
      }`}
    >
      <div className="mx-auto max-w-7xl h-full flex items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="h-8 w-8 rounded-lg bg-[#ff2d78] grid place-items-center font-bold text-[#1a0010] text-sm transition-all group-hover:shadow-[0_0_20px_rgba(255,45,120,0.6)]">
            V
          </div>
          <span className="font-bold tracking-tight text-[#e8e0f0] text-xl hidden sm:inline font-headline">
            VoxFlow
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-8 text-sm text-[#a098b0] font-label">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className="hover:text-[#ff2d78] transition-colors duration-200"
            >
              {l.label}
            </Link>
          ))}
        </nav>

        <div className="hidden md:flex items-center gap-3">
          <Link
            href="/sign-in"
            className="text-sm font-label text-[#a098b0] hover:text-[#ff2d78] transition-colors duration-200 px-3 py-1.5"
          >
            Sign In
          </Link>
          <Link
            href="/sign-up"
            className="text-sm font-headline font-bold px-5 py-2 rounded-xl bg-[#ff2d78] text-[#1a0010] hover:shadow-[0_0_20px_rgba(255,45,120,0.5)] transition-all duration-200 active:scale-95"
          >
            Request Pilot
          </Link>
        </div>

        <button
          className="md:hidden text-[#a098b0] hover:text-[#e8e0f0] transition-colors"
          onClick={() => setOpen(!open)}
          aria-label="Toggle menu"
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {open && (
        <div className="md:hidden border-b border-[#302840]/50 bg-[#0a0a12]/95 backdrop-blur-xl">
          <div className="px-4 py-4 space-y-1">
            {links.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                onClick={() => setOpen(false)}
                className="block text-sm font-label text-[#a098b0] hover:text-[#ff2d78] px-3 py-2.5 rounded-lg hover:bg-[#1e1e30] transition-colors"
              >
                {l.label}
              </Link>
            ))}
            <hr className="border-[#302840]/40 my-2" />
            <Link
              href="/sign-in"
              onClick={() => setOpen(false)}
              className="block text-sm font-label text-[#a098b0] hover:text-[#ff2d78] px-3 py-2.5 rounded-lg hover:bg-[#1e1e30] transition-colors"
            >
              Sign In
            </Link>
            <Link
              href="/sign-up"
              onClick={() => setOpen(false)}
              className="block text-sm font-headline font-bold text-[#1a0010] bg-[#ff2d78] px-3 py-2.5 rounded-xl text-center hover:shadow-[0_0_20px_rgba(255,45,120,0.5)] transition-colors"
            >
              Request Pilot
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
