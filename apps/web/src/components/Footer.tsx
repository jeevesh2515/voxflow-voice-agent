"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Footer() {
  const pathname = usePathname();
  if (pathname.startsWith("/dashboard")) return null;

  return (
    <footer
      className="bg-[#030308]/90 pt-16 sm:pt-20 pb-8 sm:pb-12 border-t border-white/[0.06] relative z-10"
      role="contentinfo"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-10 sm:gap-12 lg:gap-16 mb-12 sm:mb-16">
          <div className="space-y-5 sm:space-y-6">
            <div className="flex items-center gap-2.5">
              <span
                className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#5EEAD4]/10 border border-[#5EEAD4]/20 text-[#5EEAD4]"
                aria-hidden="true"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M2 10v4" />
                  <path d="M6 6v12" />
                  <path d="M10 3v18" />
                  <path d="M14 8v8" />
                  <path d="M18 5v14" />
                  <path d="M22 10v4" />
                </svg>
              </span>
              <span className="text-lg sm:text-xl font-headline font-bold text-white">
                VOX<span className="text-[#5EEAD4]">FLOW</span>
              </span>
            </div>
            <p className="text-white/60 text-sm sm:text-base font-body leading-relaxed">
              The voice layer for modern operations. Automated, secure, and built for scale.
            </p>
            <div className="flex gap-3 sm:gap-4">
              <a
                className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-white/[0.04] border border-white/[0.08] flex items-center justify-center hover:bg-[#5EEAD4]/10 hover:text-[#5EEAD4] text-white/70 transition-colors"
                href="https://github.com/jeevesh2515/voxflow-voice-agent"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="GitHub Repository"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <polyline points="16 18 22 12 16 6" />
                  <polyline points="8 6 2 12 8 18" />
                </svg>
              </a>
            </div>
          </div>

          <div className="space-y-4">
            <h4 className="font-mono text-xs uppercase tracking-widest text-white/80 mb-4">
              Product
            </h4>
            <ul className="space-y-2.5 sm:space-y-3">
              <li>
                <Link
                  className="text-sm sm:text-base text-white/60 hover:text-[#5EEAD4] transition-colors"
                  href="/#section-04"
                >
                  Platform
                </Link>
              </li>
              <li>
                <Link
                  className="text-sm sm:text-base text-white/60 hover:text-[#5EEAD4] transition-colors"
                  href="/#section-07"
                >
                  Integrations
                </Link>
              </li>
              <li>
                <Link
                  className="text-sm sm:text-base text-white/60 hover:text-[#5EEAD4] transition-colors"
                  href="/pricing"
                >
                  Pricing
                </Link>
              </li>
            </ul>
          </div>

          <div className="space-y-4">
            <h4 className="font-mono text-xs uppercase tracking-widest text-white/80 mb-4">
              Company
            </h4>
            <ul className="space-y-2.5 sm:space-y-3">
              <li>
                <Link
                  className="text-sm sm:text-base text-white/60 hover:text-[#5EEAD4] transition-colors"
                  href="/about"
                >
                  About Us
                </Link>
              </li>
              <li>
                <Link
                  className="text-sm sm:text-base text-white/60 hover:text-[#5EEAD4] transition-colors"
                  href="/contact"
                >
                  Contact &amp; Support
                </Link>
              </li>
            </ul>
          </div>

          <div className="space-y-4">
            <h4 className="font-mono text-xs uppercase tracking-widest text-white/80 mb-4">
              Compliance
            </h4>
            <ul className="space-y-2.5 sm:space-y-3">
              <li>
                <span className="text-sm sm:text-base text-white/60">
                  UK GDPR • eu-west-2
                </span>
              </li>
              <li>
                <Link
                  className="text-sm sm:text-base text-white/60 hover:text-[#5EEAD4] transition-colors"
                  href="/privacy"
                >
                  Privacy Policy &amp; Security
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-white/[0.06] pt-6 sm:pt-8 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p className="text-white/40 text-xs sm:text-sm font-body">
            &copy; 2026 Voxflow AI. Voice Operations. Automated.
          </p>
          <div className="flex gap-4 sm:gap-6">
            <span className="text-white/40 text-xs sm:text-sm font-mono">
              Status: Operational
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
