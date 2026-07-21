import Link from "next/link";

export default function Footer() {
  return (
    <footer
      className="bg-surface-container-lowest pt-16 sm:pt-20 pb-8 sm:pb-12 border-t border-outline-variant/15 reveal"
      role="contentinfo"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-10 sm:gap-12 lg:gap-16 mb-12 sm:mb-16">
          <div className="space-y-5 sm:space-y-6">
            <div className="flex items-center gap-2">
              <span
                className="material-symbols-outlined text-primary text-2xl sm:text-3xl font-bold"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                graphic_eq
              </span>
              <span className="text-lg sm:text-xl font-headline font-bold text-on-surface">
                VoxFlow
              </span>
            </div>
            <p className="text-on-surface-variant text-sm sm:text-base font-body leading-relaxed">
              The voice layer for modern operations. Automated, secure, and built for scale.
            </p>
            <div className="flex gap-3 sm:gap-4">
              <a
                className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-surface-variant flex items-center justify-center hover:bg-primary/20 transition-colors"
                href="#"
                aria-label="Twitter"
              >
                <span className="material-symbols-outlined text-sm">
                  alternate_email
                </span>
              </a>
              <a
                className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-surface-variant flex items-center justify-center hover:bg-primary/20 transition-colors"
                href="#"
                aria-label="LinkedIn"
              >
                <span className="material-symbols-outlined text-sm">hub</span>
              </a>
              <a
                className="w-8 h-8 sm:w-9 sm:h-9 rounded-lg bg-surface-variant flex items-center justify-center hover:bg-primary/20 transition-colors"
                href="#"
                aria-label="GitHub"
              >
                <span className="material-symbols-outlined text-sm">code</span>
              </a>
            </div>
          </div>

          <div className="space-y-4">
            <h4 className="font-label text-xs uppercase tracking-widest text-on-surface mb-4">
              Product
            </h4>
            <ul className="space-y-2.5 sm:space-y-3">
              <li>
                <Link
                  className="text-sm sm:text-base text-on-surface-variant hover:text-secondary transition-colors"
                  href="/#platform"
                >
                  Platform
                </Link>
              </li>
              <li>
                <Link
                  className="text-sm sm:text-base text-on-surface-variant hover:text-secondary transition-colors"
                  href="/#network"
                >
                  Integrations
                </Link>
              </li>
              <li>
                <Link
                  className="text-sm sm:text-base text-on-surface-variant hover:text-secondary transition-colors"
                  href="/pricing"
                >
                  Pricing
                </Link>
              </li>
            </ul>
          </div>

          <div className="space-y-4">
            <h4 className="font-label text-xs uppercase tracking-widest text-on-surface mb-4">
              Company
            </h4>
            <ul className="space-y-2.5 sm:space-y-3">
              <li>
                <Link
                  className="text-sm sm:text-base text-on-surface-variant hover:text-secondary transition-colors"
                  href="/about"
                >
                  About Us
                </Link>
              </li>
              <li>
                <Link
                  className="text-sm sm:text-base text-on-surface-variant hover:text-secondary transition-colors"
                  href="/sign-up"
                >
                  Careers
                </Link>
              </li>
            </ul>
          </div>

          <div className="space-y-4">
            <h4 className="font-label text-xs uppercase tracking-widest text-on-surface mb-4">
              Compliance
            </h4>
            <ul className="space-y-2.5 sm:space-y-3">
              <li>
                <span className="text-sm sm:text-base text-on-surface-variant">
                  SOC 2 Type II Certified
                </span>
              </li>
              <li>
                <span className="text-sm sm:text-base text-on-surface-variant">
                  Privacy Policy &amp; Security
                </span>
              </li>
            </ul>
          </div>
        </div>

        <div className="border-t border-outline-variant/15 pt-6 sm:pt-8 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p className="text-on-surface-variant text-xs sm:text-sm font-body">
            &copy; 2026 VoxFlow AI. Voice Operations. Automated.
          </p>
          <div className="flex gap-4 sm:gap-6">
            <span className="text-on-surface-variant text-xs sm:text-sm">
              Status: Operational
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
