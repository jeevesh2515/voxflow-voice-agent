import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-[#302840]/20 bg-[#0a0a12]">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-12">
          <div className="sm:col-span-2">
            <Link href="/" className="flex items-center gap-2.5 mb-4">
              <div className="h-8 w-8 rounded-lg bg-[#ff2d78] grid place-items-center font-bold text-[#1a0010] text-sm">
                V
              </div>
              <span className="font-bold tracking-tight text-[#e8e0f0] text-xl font-headline">
                VoxFlow
              </span>
            </Link>
            <p className="text-sm text-[#a098b0] leading-relaxed max-w-sm font-body">
              The voice layer for modern operations. Automated, secure, and built for scale.
            </p>
          </div>
          <div>
            <h4 className="text-xs font-label uppercase tracking-widest text-[#e8e0f0] mb-4">
              Product
            </h4>
            <div className="flex flex-col gap-3">
              <Link href="/pricing" className="text-sm text-[#a098b0] hover:text-[#00ffcc] transition-colors">
                Pricing
              </Link>
              <Link href="/#platform" className="text-sm text-[#a098b0] hover:text-[#00ffcc] transition-colors">
                Platform
              </Link>
              <Link href="/about" className="text-sm text-[#a098b0] hover:text-[#00ffcc] transition-colors">
                About VoxFlow
              </Link>
            </div>
          </div>
          <div>
            <h4 className="text-xs font-label uppercase tracking-widest text-[#e8e0f0] mb-4">
              Support
            </h4>
            <div className="flex flex-col gap-3">
              <Link href="/sign-in" className="text-sm text-[#a098b0] hover:text-[#00ffcc] transition-colors">
                Sign In
              </Link>
              <Link href="/sign-up" className="text-sm text-[#a098b0] hover:text-[#00ffcc] transition-colors">
                Request Pilot
              </Link>
            </div>
          </div>
        </div>
        <div className="mt-12 pt-6 border-t border-[#302840]/20 flex flex-col sm:flex-row items-center justify-between gap-3">
          <span className="text-xs text-[#a098b0] font-body">
            &copy; 2026 VoxFlow AI. Voice Operations. Automated.
          </span>
          <span className="text-[10px] font-label uppercase tracking-widest text-[#a098b0] border border-[#302840]/40 px-2.5 py-1 rounded-md">
            SOC2 Type II Certified
          </span>
        </div>
      </div>
    </footer>
  );
}
