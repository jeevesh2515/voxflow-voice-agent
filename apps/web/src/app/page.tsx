import Link from "next/link";
import { ArrowRight, Mic, PhoneCall, Boxes, Package, ShieldCheck } from "lucide-react";

export default function Home() {
  return (
    <div className="min-h-screen bg-ink-950 text-ink-100">
      {/* Hero */}
      <header className="px-8 py-6 flex items-center justify-between border-b border-ink-800/60">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-md bg-gradient-to-br from-vox-500 to-vox-700 grid place-items-center font-bold text-white text-sm">V</div>
          <span className="font-semibold tracking-tight">VoxFlow Voice Agent</span>
        </div>
        <nav className="flex items-center gap-6 text-sm text-ink-300">
          <Link href="#how" className="hover:text-ink-50">How it works</Link>
          <Link href="/dashboard" className="hover:text-ink-50">Dashboard</Link>
          <Link
            href="https://github.com/jeevesh2515/voxflow-voice-agent"
            className="text-ink-400 hover:text-ink-50"
            target="_blank"
          >
            GitHub ↗
          </Link>
        </nav>
      </header>

      <section className="px-8 py-20 max-w-5xl mx-auto text-center">
        <div className="inline-flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-ink-400 border border-ink-700/60 rounded-full px-3 py-1 mb-6">
          <span className="h-1.5 w-1.5 rounded-full bg-vox-500 animate-pulse" />
          Self-hostable · Hindi + English · Zero cost to start
        </div>
        <h1 className="text-4xl md:text-6xl font-semibold tracking-tight leading-[1.05] text-ink-50">
          Every supplier call. <span className="text-vox-400">Every detail.</span> Handled.
        </h1>
        <p className="mt-6 text-lg text-ink-300 max-w-2xl mx-auto leading-relaxed">
          VoxFlow picks up inbound supplier calls, captures POs, checks stock, shares shipment
          status, and logs everything — in Hindi or English, around the clock.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md bg-vox-500 hover:bg-vox-600 text-white text-sm font-medium shadow-glow"
          >
            Open dashboard <ArrowRight size={16} />
          </Link>
          <Link
            href="/dashboard/simulator"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md bg-ink-800 hover:bg-ink-700 text-ink-100 text-sm font-medium border border-ink-700"
          >
            <Mic size={16} /> Try the phone simulator
          </Link>
        </div>
      </section>

      <section id="how" className="px-8 py-16 max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { icon: PhoneCall, title: "Listens in Hindi + English", body: "Bilingual voice pipeline. STT auto-detects; replies in the caller's language." },
          { icon: Boxes,     title: "Pulls from your data",      body: "Stock, shipments, and supplier records — never invented, always approved." },
          { icon: Package,   title: "Captures POs end-to-end",  body: "Reads items back, confirms with the caller, and writes a structured order." },
          { icon: ShieldCheck, title: "Escalates when needed",   body: "Pricing exceptions, complaints, anything sensitive — straight to a human queue." },
          { icon: Mic,       title: "Browser phone simulator",   body: "Demo the agent in your browser with your own microphone. No telephony needed." },
          { icon: ArrowRight, title: "Drop-in for your business", body: "Per-business prompts, SKUs, warehouses. Self-host or run on free tiers." },
        ].map(({ icon: Icon, title, body }) => (
          <div key={title} className="rounded-lg border border-ink-700/60 bg-ink-900/40 p-5 hover:border-vox-500/40 transition-colors">
            <Icon className="text-vox-400 mb-3" size={20} />
            <h3 className="text-sm font-semibold text-ink-50 mb-1">{title}</h3>
            <p className="text-sm text-ink-300 leading-relaxed">{body}</p>
          </div>
        ))}
      </section>

      <footer className="border-t border-ink-800/60 px-8 py-6 text-center text-xs text-ink-500 font-mono">
        <div>VoxFlow Voice Agent · MIT · v0.1.0</div>
        <div className="opacity-50 mt-2">
          <a href="https://madethis.com/r/8fsktqhe" className="hover:opacity-75">Built with MadeThis</a>
        </div>
      </footer>
    </div>
  );
}
