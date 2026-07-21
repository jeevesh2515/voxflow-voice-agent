import Link from "next/link";

export default function Footer() {
  return (
    <footer className="border-t border-border bg-background">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8 lg:gap-12">
          <div className="sm:col-span-2">
            <Link href="/" className="flex items-center gap-2.5 mb-4">
              <div className="h-8 w-8 rounded-lg bg-primary grid place-items-center font-bold text-primary-foreground text-sm">
                V
              </div>
              <span className="font-semibold tracking-tight text-foreground text-lg">
                VoxFlow Voice Agent
              </span>
            </Link>
            <p className="text-sm text-muted-foreground leading-relaxed max-w-sm">
              The voice layer for modern operations&mdash;built for scale and trusted by the teams behind every detail.
            </p>
          </div>
          <div>
            <h4 className="text-xs font-semibold tracking-[0.12em] uppercase text-muted-foreground mb-4">
              Product
            </h4>
            <div className="flex flex-col gap-3">
              <Link href="/pricing" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Pricing
              </Link>
              <Link href="/blog" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Resources
              </Link>
              <Link href="/about" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                About VoxFlow Voice Agent
              </Link>
            </div>
          </div>
          <div>
            <h4 className="text-xs font-semibold tracking-[0.12em] uppercase text-muted-foreground mb-4">
              Support
            </h4>
            <div className="flex flex-col gap-3">
              <Link href="/sign-in" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Sign In
              </Link>
              <Link href="/sign-up" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Get started
              </Link>
            </div>
          </div>
        </div>
        <div className="mt-12 pt-6 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-3">
          <span className="text-xs text-muted-foreground">
            &copy; 2026 VoxFlow Voice Agent. All rights reserved.
          </span>
          <a
            href="https://madethis.com"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[10px] font-mono uppercase tracking-[0.12em] text-muted-foreground hover:text-foreground transition-colors rounded-sm border border-border/50 px-2 py-1"
          >
            Built with MadeThis
          </a>
        </div>
      </div>
    </footer>
  );
}
