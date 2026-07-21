"use client";

import Link from "next/link";
import { useEffect } from "react";

export default function Home() {
  useEffect(() => {
    // 1. Scroll reveal
    const els = document.querySelectorAll(
      ".reveal, .reveal-left, .reveal-right, .reveal-scale, .stagger-children"
    );
    if (els.length > 0) {
      const obs = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add("visible");
              obs.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.08, rootMargin: "0px 0px -40px 0px" }
      );
      els.forEach((el) => obs.observe(el));
    }

    // 2. Floating particles
    const container = document.getElementById("particles-canvas");
    if (container && container.childElementCount === 0) {
      const count = window.innerWidth < 768 ? 15 : 30;
      const colors = ["var(--neon-primary)", "var(--neon-secondary)", "var(--neon-tertiary)"];
      for (let i = 0; i < count; i++) {
        const p = document.createElement("div");
        p.className = "particle";
        p.style.left = Math.random() * 100 + "%";
        p.style.top = Math.random() * 100 + "%";
        p.style.background = colors[i % 3];
        p.style.boxShadow = "0 0 6px " + colors[i % 3];
        const sz = 1 + Math.random() * 2 + "px";
        p.style.width = sz;
        p.style.height = sz;
        const dur = 4 + Math.random() * 8;
        const delay = Math.random() * 10;
        p.style.animation = `particle-float ${dur}s ease-in-out ${delay}s infinite alternate`;
        container.appendChild(p);
      }
    }

    // 3. Custom cursor
    const dot = document.getElementById("cursorDot");
    const ring = document.getElementById("cursorRing");
    if (dot && ring) {
      let mouseX = 0, mouseY = 0;
      let ringX = 0, ringY = 0;

      const onMouseMove = (e: MouseEvent) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
        dot.style.left = mouseX + "px";
        dot.style.top = mouseY + "px";
      };
      window.addEventListener("mousemove", onMouseMove);

      let animId: number;
      const animateRing = () => {
        ringX += (mouseX - ringX) * 0.12;
        ringY += (mouseY - ringY) * 0.12;
        ring.style.left = ringX + "px";
        ring.style.top = ringY + "px";
        animId = requestAnimationFrame(animateRing);
      };
      animateRing();

      return () => {
        window.removeEventListener("mousemove", onMouseMove);
        cancelAnimationFrame(animId);
      };
    }
  }, []);

  return (
    <>
      {/* Custom Cursor Elements */}
      <div className="cursor-dot" id="cursorDot" aria-hidden="true" />
      <div className="cursor-ring" id="cursorRing" aria-hidden="true" />

      {/* Floating Particles Container */}
      <div
        id="particles-canvas"
        className="fixed inset-0 pointer-events-none z-0 overflow-hidden"
        aria-hidden="true"
      />

      <main className="relative z-10">
        {/* ==================== HERO SECTION ==================== */}
        <section
          className="relative min-h-screen flex items-center pt-24 pb-16 sm:pt-28 sm:pb-24 overflow-hidden grid-bg"
          id="hero"
        >
          {/* Glow Orbs */}
          <div
            className="absolute top-1/4 left-1/4 w-[40vw] h-[40vw] max-w-[500px] max-h-[500px] bg-primary/10 blur-[120px] rounded-full pulse-glow pointer-events-none"
            aria-hidden="true"
          />
          <div
            className="absolute bottom-1/4 right-1/4 w-[35vw] h-[35vw] max-w-[400px] max-h-[400px] bg-secondary/10 blur-[120px] rounded-full animate-float-delayed pointer-events-none"
            aria-hidden="true"
          />
          <div
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[60vw] h-[60vw] max-w-[600px] max-h-[600px] bg-primary/5 blur-[150px] rounded-full pointer-events-none"
            aria-hidden="true"
          />

          <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid lg:grid-cols-2 gap-8 lg:gap-16 items-center">
            {/* Left Hero Content */}
            <div className="reveal stagger-children" id="hero-content">
              <div>
                <span
                  className="font-label text-secondary tracking-[0.2em] uppercase text-xs sm:text-sm mb-4 sm:mb-6 block neon-text-sm"
                  role="text"
                >
                  <span aria-hidden="true">✦</span> Next-Gen Voice Operations
                </span>
                <h1 className="font-headline font-extrabold text-4xl sm:text-5xl lg:text-7xl xl:text-8xl leading-[1.1] tracking-tight mb-6 text-on-surface">
                  Every&nbsp;call.<br />
                  Every&nbsp;detail.<br />
                  <span className="text-primary neon-text">Handled.</span>
                </h1>
                <p className="text-on-surface-variant text-base sm:text-lg lg:text-xl mb-8 sm:mb-10 max-w-md font-body leading-relaxed">
                  VoxFlow is the voice layer for modern operations — built for scale, trusted by leading teams to automate high-stakes conversations.
                </p>
                <div className="flex flex-wrap gap-3 sm:gap-4">
                  <Link
                    href="/sign-up"
                    className="group inline-flex items-center gap-2 bg-primary text-on-primary px-6 sm:px-8 py-3 sm:py-4 font-headline font-bold rounded-xl transition-all duration-300 hover:shadow-[0_0_30px_rgba(255,45,120,0.5)] hover:scale-[1.03] active:scale-95 text-sm sm:text-base"
                  >
                    Request Pilot
                    <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">
                      arrow_forward
                    </span>
                  </Link>
                  <a
                    href="#platform"
                    className="inline-flex items-center gap-2 border border-outline-variant/50 text-on-surface px-6 sm:px-8 py-3 sm:py-4 font-headline font-bold rounded-xl hover:bg-surface-variant transition-all duration-300 hover:border-primary/40 active:scale-95 text-sm sm:text-base"
                  >
                    Explore Operations
                  </a>
                </div>
              </div>
            </div>

            {/* Right Dashboard Mockup */}
            <div className="relative reveal-right" id="hero-dashboard">
              <div className="animate-float">
                <div
                  className="absolute -inset-2 bg-gradient-to-r from-primary/15 to-secondary/15 blur-3xl rounded-3xl pointer-events-none"
                  aria-hidden="true"
                />
                <div className="relative glass neon-border rounded-2xl overflow-hidden shadow-2xl border-outline-variant/20">
                  {/* Browser Chrome */}
                  <div className="bg-surface-variant/80 px-3 sm:px-4 py-2.5 sm:py-3 flex items-center gap-2 border-b border-outline-variant/20">
                    <div className="flex gap-1.5" aria-hidden="true">
                      <div className="w-2.5 h-2.5 rounded-full bg-red-500/40" />
                      <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/40" />
                      <div className="w-2.5 h-2.5 rounded-full bg-green-500/40" />
                    </div>
                    <div className="mx-auto bg-surface-container px-3 py-1 rounded text-[10px] text-on-surface-variant font-label border border-outline-variant/20 flex items-center gap-2 max-w-[200px] truncate">
                      <span className="material-symbols-outlined text-[12px] shrink-0">
                        lock
                      </span>
                      <span className="truncate">app.voxflow.ai/operations</span>
                    </div>
                    <div className="w-14" aria-hidden="true" />
                  </div>

                  {/* Dashboard Body */}
                  <div className="p-3 sm:p-5 md:p-6 grid grid-cols-12 gap-3 sm:gap-4">
                    {/* Sidebar */}
                    <div className="col-span-3 space-y-2 sm:space-y-3">
                      <div className="bg-primary/10 border border-primary/30 p-1.5 sm:p-2 rounded-lg text-[10px] text-primary flex items-center gap-1.5 sm:gap-2">
                        <span className="material-symbols-outlined text-[12px] sm:text-[14px]">
                          dashboard
                        </span>
                        <span className="hidden sm:inline">Overview</span>
                      </div>
                      <div className="p-1.5 sm:p-2 rounded-lg text-[10px] text-on-surface-variant flex items-center gap-1.5 sm:gap-2 hover:bg-surface-variant transition-colors">
                        <span className="material-symbols-outlined text-[12px] sm:text-[14px]">
                          call
                        </span>
                        <span className="hidden sm:inline">Calls</span>
                      </div>
                      <div className="p-1.5 sm:p-2 rounded-lg text-[10px] text-on-surface-variant flex items-center gap-1.5 sm:gap-2 hover:bg-surface-variant transition-colors">
                        <span className="material-symbols-outlined text-[12px] sm:text-[14px]">
                          inventory_2
                        </span>
                        <span className="hidden sm:inline">Orders</span>
                      </div>
                      <div className="p-1.5 sm:p-2 rounded-lg text-[10px] text-on-surface-variant flex items-center gap-1.5 sm:gap-2 hover:bg-surface-variant transition-colors">
                        <span className="material-symbols-outlined text-[12px] sm:text-[14px]">
                          account_circle
                        </span>
                        <span className="hidden sm:inline">Contacts</span>
                      </div>
                    </div>

                    {/* Console Main Content */}
                    <div className="col-span-9 space-y-3 sm:space-y-4">
                      <div className="flex justify-between items-center mb-1 sm:mb-2">
                        <h3 className="font-headline font-bold text-xs sm:text-sm text-on-surface">
                          Live Operations
                        </h3>
                        <span className="flex items-center gap-1.5 text-[9px] sm:text-[10px] text-secondary font-label">
                          <span className="w-1.5 h-1.5 bg-secondary rounded-full animate-pulse" />
                          All systems active
                        </span>
                      </div>

                      {/* Stat Cards */}
                      <div className="grid grid-cols-3 gap-2 sm:gap-3">
                        <div className="bg-surface-container-high/80 p-2 sm:p-3 rounded-lg border border-outline-variant/20">
                          <p className="text-[8px] sm:text-[9px] text-on-surface-variant mb-1">
                            Live Calls
                          </p>
                          <p className="text-base sm:text-xl font-headline font-bold text-on-surface">
                            12
                          </p>
                          <div className="h-3 sm:h-4 flex items-end gap-0.5 mt-1 sm:mt-2 overflow-hidden">
                            <div className="waveform-bar w-1 bg-primary/40" style={{ animationDelay: "0.1s" }} />
                            <div className="waveform-bar w-1 bg-primary/60" style={{ animationDelay: "0.3s" }} />
                            <div className="waveform-bar w-1 bg-primary" style={{ animationDelay: "0.5s" }} />
                            <div className="waveform-bar w-1 bg-primary/70" style={{ animationDelay: "0.2s" }} />
                            <div className="waveform-bar w-1 bg-primary/40" style={{ animationDelay: "0.4s" }} />
                          </div>
                        </div>
                        <div className="bg-surface-container-high/80 p-2 sm:p-3 rounded-lg border border-outline-variant/20">
                          <p className="text-[8px] sm:text-[9px] text-on-surface-variant mb-1">
                            Calls Handled
                          </p>
                          <p className="text-base sm:text-xl font-headline font-bold text-on-surface">
                            48
                          </p>
                          <p className="text-[7px] sm:text-[8px] text-secondary mt-1">
                            +18% Today
                          </p>
                        </div>
                        <div className="bg-surface-container-high/80 p-2 sm:p-3 rounded-lg border border-outline-variant/20">
                          <p className="text-[8px] sm:text-[9px] text-on-surface-variant mb-1">
                            Orders
                          </p>
                          <p className="text-base sm:text-xl font-headline font-bold text-on-surface">
                            223
                          </p>
                          <p className="text-[7px] sm:text-[8px] text-secondary mt-1">
                            +24% Today
                          </p>
                        </div>
                      </div>

                      {/* Active Call Card */}
                      <div className="bg-surface-container-highest/80 p-2 sm:p-3 rounded-lg border border-primary/15 relative overflow-hidden">
                        <div
                          className="absolute top-0 right-0 w-20 h-20 bg-primary/5 blur-2xl rounded-full pointer-events-none"
                          aria-hidden="true"
                        />
                        <div className="flex justify-between items-center mb-2 sm:mb-3 relative">
                          <div className="flex items-center gap-1.5 sm:gap-2">
                            <span className="material-symbols-outlined text-primary text-sm">
                              support_agent
                            </span>
                            <span className="text-[9px] sm:text-[10px] font-bold text-on-surface">
                              Active Call: Customer #8292
                            </span>
                          </div>
                          <span className="bg-primary/20 text-primary text-[7px] sm:text-[8px] px-1.5 py-0.5 rounded uppercase font-bold tracking-wider">
                            Live
                          </span>
                        </div>
                        <div className="space-y-1.5 sm:space-y-2 relative">
                          <div className="flex gap-1.5 sm:gap-2">
                            <div className="w-3 h-3 sm:w-4 sm:h-4 rounded-full bg-secondary/20 flex-shrink-0 mt-0.5" />
                            <div className="bg-surface-variant/50 p-1.5 sm:p-2 rounded-r-lg rounded-bl-lg text-[8px] sm:text-[9px] text-on-surface-variant italic leading-relaxed max-w-[80%]">
                              &ldquo;I&apos;d like to check the status of my recent shipment for order #9921.&rdquo;
                            </div>
                          </div>
                          <div className="flex gap-1.5 sm:gap-2 justify-end">
                            <div className="bg-primary/10 p-1.5 sm:p-2 rounded-l-lg rounded-br-lg text-[8px] sm:text-[9px] text-on-surface border border-primary/10 leading-relaxed max-w-[85%]">
                              &ldquo;Checking order #9921 now. It&apos;s currently in transit and expected to arrive by Tuesday.&rdquo;
                            </div>
                            <div className="w-3 h-3 sm:w-4 sm:h-4 rounded-full bg-primary/20 flex-shrink-0 mt-0.5" />
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ==================== TRUSTED BY SECTION ==================== */}
        <section
          className="py-10 sm:py-12 border-y border-outline-variant/15 relative overflow-hidden reveal"
          id="trusted"
        >
          <div className="noise absolute inset-0 pointer-events-none" aria-hidden="true" />
          <p className="text-center text-on-surface-variant font-label text-xs tracking-[0.2em] uppercase mb-6 sm:mb-8 relative z-10">
            Trusted by industry leaders
          </p>
          <div className="marquee-track relative z-10">
            <div className="marquee-content">
              {[
                { name: "ZENITH-TECH", icon: "token" },
                { name: "NEXUS_AI", icon: "polyline" },
                { name: "CORP_CORE", icon: "grid_view" },
                { name: "PLATFORM_X", icon: "hub" },
                { name: "ZENITH-TECH", icon: "token" },
                { name: "NEXUS_AI", icon: "polyline" },
                { name: "CORP_CORE", icon: "grid_view" },
              ].map((brand, idx) => (
                <div
                  key={idx}
                  className="flex items-center gap-2 sm:gap-3 grayscale opacity-30 hover:grayscale-0 hover:opacity-100 transition-all duration-500 cursor-default group"
                  role="img"
                  aria-label={brand.name}
                >
                  <span className="material-symbols-outlined text-2xl sm:text-3xl text-on-surface">
                    {brand.icon}
                  </span>
                  <span className="font-headline font-bold text-lg sm:text-xl tracking-tight text-on-surface">
                    {brand.name}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ==================== FEATURES SECTION ==================== */}
        <section className="py-20 sm:py-28 lg:py-32 relative grid-bg" id="platform">
          <div className="absolute inset-0 noise pointer-events-none" aria-hidden="true" />
          <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-14 sm:mb-20 reveal">
              <span className="font-label text-secondary tracking-[0.2em] uppercase text-xs mb-3 sm:mb-4 block neon-text-sm">
                Platform
              </span>
              <h2 className="font-headline font-bold text-3xl sm:text-4xl lg:text-5xl mb-4 tracking-tight text-on-surface">
                Enterprise Grade Intelligence
              </h2>
              <p className="text-on-surface-variant text-base sm:text-lg max-w-2xl mx-auto font-body">
                Standardize every customer interaction with surgical precision and persistent context.
              </p>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5 sm:gap-6 lg:gap-8 stagger-children" id="features-grid">
              <div className="glass rounded-2xl neon-border-card p-6 sm:p-8 transition-all duration-400 group hover:-translate-y-1 relative overflow-hidden">
                <div
                  className="absolute top-0 right-0 w-32 h-32 bg-primary/3 blur-3xl rounded-full pointer-events-none group-hover:bg-primary/8 transition-all duration-500"
                  aria-hidden="true"
                />
                <div className="w-12 h-12 sm:w-14 sm:h-14 bg-surface-container-high rounded-xl flex items-center justify-center mb-5 sm:mb-6 border border-outline-variant/20 group-hover:scale-110 transition-transform duration-400 relative">
                  <span
                    className="material-symbols-outlined text-secondary text-2xl sm:text-3xl"
                    style={{ fontVariationSettings: "'FILL' 1" }}
                  >
                    waves
                  </span>
                </div>
                <h3 className="font-headline font-bold text-lg sm:text-xl mb-3 sm:mb-4 text-on-surface">
                  Unmatched Consistency
                </h3>
                <p className="text-on-surface-variant text-sm sm:text-base leading-relaxed font-body">
                  Ensure every agent adheres to brand protocols perfectly. Zero variability in tone, accuracy, or professional compliance.
                </p>
              </div>

              <div className="glass rounded-2xl neon-border-card p-6 sm:p-8 transition-all duration-400 group hover:-translate-y-1 relative overflow-hidden">
                <div
                  className="absolute top-0 right-0 w-32 h-32 bg-primary/3 blur-3xl rounded-full pointer-events-none group-hover:bg-primary/8 transition-all duration-500"
                  aria-hidden="true"
                />
                <div className="w-12 h-12 sm:w-14 sm:h-14 bg-surface-container-high rounded-xl flex items-center justify-center mb-5 sm:mb-6 border border-outline-variant/20 group-hover:scale-110 transition-transform duration-400 relative">
                  <span
                    className="material-symbols-outlined text-primary text-2xl sm:text-3xl"
                    style={{ fontVariationSettings: "'FILL' 1" }}
                  >
                    database
                  </span>
                </div>
                <h3 className="font-headline font-bold text-lg sm:text-xl mb-3 sm:mb-4 text-on-surface">
                  Operational Memory
                </h3>
                <p className="text-on-surface-variant text-sm sm:text-base leading-relaxed font-body">
                  Integrated real-time database access allows agents to remember history, preferences, and complex order details across sessions.
                </p>
              </div>

              <div className="glass rounded-2xl border border-tertiary/15 hover:border-tertiary/40 p-6 sm:p-8 transition-all duration-400 group hover:-translate-y-1 relative overflow-hidden">
                <div
                  className="absolute top-0 right-0 w-32 h-32 bg-tertiary/3 blur-3xl rounded-full pointer-events-none group-hover:bg-tertiary/8 transition-all duration-500"
                  aria-hidden="true"
                />
                <div className="w-12 h-12 sm:w-14 sm:h-14 bg-surface-container-high rounded-xl flex items-center justify-center mb-5 sm:mb-6 border border-outline-variant/20 group-hover:scale-110 transition-transform duration-400 relative">
                  <span
                    className="material-symbols-outlined text-tertiary text-2xl sm:text-3xl"
                    style={{ fontVariationSettings: "'FILL' 1" }}
                  >
                    shield_lock
                  </span>
                </div>
                <h3 className="font-headline font-bold text-lg sm:text-xl mb-3 sm:mb-4 text-on-surface">
                  Strategic Control
                </h3>
                <p className="text-on-surface-variant text-sm sm:text-base leading-relaxed font-body">
                  Complete visibility into every dialogue path. Instant audit logs and real-time intervention for edge cases.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* ==================== SCALE SECTION ==================== */}
        <section className="py-20 sm:py-28 lg:py-32 bg-surface-container-lowest relative overflow-hidden" id="solutions">
          <div className="absolute top-0 left-0 w-64 h-64 bg-primary/5 blur-[120px] rounded-full pointer-events-none" aria-hidden="true" />
          <div className="absolute bottom-0 right-0 w-64 h-64 bg-secondary/5 blur-[120px] rounded-full pointer-events-none" aria-hidden="true" />
          <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid lg:grid-cols-2 gap-12 lg:gap-20 items-center">
            <div className="reveal-left">
              <span className="font-label text-secondary tracking-[0.2em] uppercase text-xs mb-3 sm:mb-4 block neon-text-sm">
                Scale
              </span>
              <h2 className="font-headline font-extrabold text-3xl sm:text-4xl lg:text-5xl xl:text-6xl mb-6 tracking-tight leading-tight text-on-surface">
                Built for <span className="text-primary neon-text">Scale.</span>
              </h2>
              <p className="text-on-surface-variant text-base sm:text-lg lg:text-xl leading-relaxed mb-8 font-body">
                Handle 10,000+ simultaneous inquiries without breaking a sweat. VoxFlow&apos;s infrastructure is distributed across low-latency edge nodes for instantaneous response times.
              </p>
              <div className="flex flex-wrap items-center gap-4 sm:gap-6">
                <div className="flex -space-x-3">
                  <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-full border-2 border-background bg-surface-variant" aria-hidden="true" />
                  <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-full border-2 border-background bg-primary" aria-hidden="true" />
                  <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-full border-2 border-background bg-secondary" aria-hidden="true" />
                </div>
                <p className="text-xs sm:text-sm font-label text-on-surface-variant">
                  <span className="text-on-surface font-bold">2.4M+</span> interactions handled this month
                </p>
              </div>
            </div>

            <div className="relative reveal-right">
              <div className="relative glass neon-border rounded-2xl sm:rounded-3xl overflow-hidden p-4 sm:p-8">
                <div className="absolute -inset-1 bg-gradient-to-r from-primary/10 to-secondary/10 blur-2xl opacity-50 pointer-events-none" aria-hidden="true" />
                <div className="grid grid-cols-2 gap-4 sm:gap-6 relative">
                  <div className="bg-surface-container-high/60 rounded-xl p-4 sm:p-6 border border-outline-variant/20 text-center">
                    <span className="material-symbols-outlined text-primary text-3xl sm:text-4xl mb-2" style={{ fontVariationSettings: "'FILL' 1" }}>
                      cloud
                    </span>
                    <p className="text-lg sm:text-2xl font-headline font-bold text-on-surface">99.99%</p>
                    <p className="text-[10px] sm:text-xs text-on-surface-variant">Uptime SLA</p>
                  </div>
                  <div className="bg-surface-container-high/60 rounded-xl p-4 sm:p-6 border border-outline-variant/20 text-center">
                    <span className="material-symbols-outlined text-secondary text-3xl sm:text-4xl mb-2" style={{ fontVariationSettings: "'FILL' 1" }}>
                      bolt
                    </span>
                    <p className="text-lg sm:text-2xl font-headline font-bold text-on-surface">&lt;50ms</p>
                    <p className="text-[10px] sm:text-xs text-on-surface-variant">Avg Response</p>
                  </div>
                  <div className="bg-surface-container-high/60 rounded-xl p-4 sm:p-6 border border-outline-variant/20 text-center">
                    <span className="material-symbols-outlined text-tertiary text-3xl sm:text-4xl mb-2" style={{ fontVariationSettings: "'FILL' 1" }}>
                      language
                    </span>
                    <p className="text-lg sm:text-2xl font-headline font-bold text-on-surface">50+</p>
                    <p className="text-[10px] sm:text-xs text-on-surface-variant">Languages</p>
                  </div>
                  <div className="bg-surface-container-high/60 rounded-xl p-4 sm:p-6 border border-outline-variant/20 text-center">
                    <span className="material-symbols-outlined text-primary text-3xl sm:text-4xl mb-2" style={{ fontVariationSettings: "'FILL' 1" }}>
                      verified
                    </span>
                    <p className="text-lg sm:text-2xl font-headline font-bold text-on-surface">SOC 2</p>
                    <p className="text-[10px] sm:text-xs text-on-surface-variant">Type II Certified</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ==================== STATS STRIP ==================== */}
        <section className="py-16 sm:py-20 lg:py-24 border-t border-outline-variant/20 relative reveal" id="stats">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-8">
              <div className="text-center p-4 sm:p-6 rounded-2xl bg-surface-container/30 backdrop-blur-sm border border-outline-variant/10">
                <p className="text-3xl sm:text-4xl lg:text-5xl font-headline font-black text-primary mb-1 sm:mb-2 neon-text">99.8%</p>
                <p className="text-[10px] sm:text-xs font-label tracking-widest uppercase text-on-surface-variant">Transcription Accuracy</p>
              </div>
              <div className="text-center p-4 sm:p-6 rounded-2xl bg-surface-container/30 backdrop-blur-sm border border-outline-variant/10">
                <p className="text-3xl sm:text-4xl lg:text-5xl font-headline font-black text-secondary mb-1 sm:mb-2 neon-text-sm">&lt;100ms</p>
                <p className="text-[10px] sm:text-xs font-label tracking-widest uppercase text-on-surface-variant">Global Latency</p>
              </div>
              <div className="text-center p-4 sm:p-6 rounded-2xl bg-surface-container/30 backdrop-blur-sm border border-outline-variant/10">
                <p className="text-3xl sm:text-4xl lg:text-5xl font-headline font-black text-tertiary mb-1 sm:mb-2 neon-text-sm">SOC2</p>
                <p className="text-[10px] sm:text-xs font-label tracking-widest uppercase text-on-surface-variant">Type II Security</p>
              </div>
              <div className="text-center p-4 sm:p-6 rounded-2xl bg-surface-container/30 backdrop-blur-sm border border-outline-variant/10">
                <p className="text-3xl sm:text-4xl lg:text-5xl font-headline font-black text-on-surface mb-1 sm:mb-2">50+</p>
                <p className="text-[10px] sm:text-xs font-label tracking-widest uppercase text-on-surface-variant">Languages Supported</p>
              </div>
            </div>
          </div>
        </section>

        {/* ==================== INTEGRATIONS SHOWCASE ==================== */}
        <section className="py-20 sm:py-28 lg:py-32 relative grid-bg" id="network">
          <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-14 sm:mb-20 reveal">
              <span className="font-label text-secondary tracking-[0.2em] uppercase text-xs mb-3 sm:mb-4 block neon-text-sm">
                Integrations
              </span>
              <h2 className="font-headline font-bold text-3xl sm:text-4xl lg:text-5xl mb-4 tracking-tight text-on-surface">
                Seamless Connectivity
              </h2>
              <p className="text-on-surface-variant text-base sm:text-lg max-w-2xl mx-auto font-body">
                VoxFlow plugs directly into your existing stack. No rip and replace.
              </p>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 stagger-children" id="integrations-grid">
              <div className="glass rounded-xl sm:rounded-2xl p-5 sm:p-8 border border-outline-variant/20 hover:border-secondary/30 transition-all duration-400 group text-center hover:-translate-y-1">
                <div className="w-12 h-12 sm:w-16 sm:h-16 bg-surface-container-high rounded-2xl flex items-center justify-center mx-auto mb-4 sm:mb-5 border border-outline-variant/20 group-hover:scale-110 transition-transform duration-400">
                  <span className="material-symbols-outlined text-secondary text-2xl sm:text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                    salesforce
                  </span>
                </div>
                <h4 className="font-headline font-bold text-sm sm:text-base text-on-surface">CRM Sync</h4>
                <p className="text-on-surface-variant text-xs sm:text-sm mt-1 sm:mt-2">Real-time contact &amp; deal updates</p>
              </div>

              <div className="glass rounded-xl sm:rounded-2xl p-5 sm:p-8 border border-outline-variant/20 hover:border-secondary/30 transition-all duration-400 group text-center hover:-translate-y-1">
                <div className="w-12 h-12 sm:w-16 sm:h-16 bg-surface-container-high rounded-2xl flex items-center justify-center mx-auto mb-4 sm:mb-5 border border-outline-variant/20 group-hover:scale-110 transition-transform duration-400">
                  <span className="material-symbols-outlined text-secondary text-2xl sm:text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                    chat
                  </span>
                </div>
                <h4 className="font-headline font-bold text-sm sm:text-base text-on-surface">Slack &amp; Teams</h4>
                <p className="text-on-surface-variant text-xs sm:text-sm mt-1 sm:mt-2">Dispatch alerts &amp; summaries</p>
              </div>

              <div className="glass rounded-xl sm:rounded-2xl p-5 sm:p-8 border border-outline-variant/20 hover:border-secondary/30 transition-all duration-400 group text-center hover:-translate-y-1">
                <div className="w-12 h-12 sm:w-16 sm:h-16 bg-surface-container-high rounded-2xl flex items-center justify-center mx-auto mb-4 sm:mb-5 border border-outline-variant/20 group-hover:scale-110 transition-transform duration-400">
                  <span className="material-symbols-outlined text-secondary text-2xl sm:text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                    database
                  </span>
                </div>
                <h4 className="font-headline font-bold text-sm sm:text-base text-on-surface">Data Warehouses</h4>
                <p className="text-on-surface-variant text-xs sm:text-sm mt-1 sm:mt-2">Snowflake, BigQuery, Redshift</p>
              </div>

              <div className="glass rounded-xl sm:rounded-2xl p-5 sm:p-8 border border-outline-variant/20 hover:border-secondary/30 transition-all duration-400 group text-center hover:-translate-y-1">
                <div className="w-12 h-12 sm:w-16 sm:h-16 bg-surface-container-high rounded-2xl flex items-center justify-center mx-auto mb-4 sm:mb-5 border border-outline-variant/20 group-hover:scale-110 transition-transform duration-400">
                  <span className="material-symbols-outlined text-secondary text-2xl sm:text-3xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                    api
                  </span>
                </div>
                <h4 className="font-headline font-bold text-sm sm:text-base text-on-surface">REST &amp; Webhook</h4>
                <p className="text-on-surface-variant text-xs sm:text-sm mt-1 sm:mt-2">Custom integrations API</p>
              </div>
            </div>
          </div>
        </section>

        {/* ==================== TESTIMONIAL ==================== */}
        <section className="py-16 sm:py-20 lg:py-24 relative reveal" id="testimonial">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <div className="glass rounded-2xl sm:rounded-3xl p-8 sm:p-12 lg:p-16 border border-outline-variant/20 relative overflow-hidden">
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-48 bg-primary/5 blur-[100px] rounded-full pointer-events-none" aria-hidden="true" />
              <div className="relative">
                <span className="material-symbols-outlined text-primary/20 text-5xl sm:text-6xl block mb-4 sm:mb-6" style={{ fontVariationSettings: "'FILL' 1" }}>
                  format_quote
                </span>
                <blockquote className="text-lg sm:text-xl lg:text-2xl font-body leading-relaxed text-on-surface mb-6 sm:mb-8 italic">
                  &ldquo;VoxFlow transformed our call center overnight. We scaled from 50 to 5,000 daily calls without adding a single agent. The accuracy is unreal.&rdquo;
                </blockquote>
                <div className="flex items-center justify-center gap-3 sm:gap-4">
                  <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center text-white font-headline font-bold text-sm sm:text-base" aria-hidden="true">
                    S
                  </div>
                  <div className="text-left">
                    <p className="font-headline font-bold text-sm sm:text-base text-on-surface">Sarah Chen</p>
                    <p className="text-on-surface-variant text-xs sm:text-sm">VP of Operations, ZenithTech</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ==================== CTA SECTION ==================== */}
        <section className="py-20 sm:py-28 lg:py-32 relative grid-bg" id="cta">
          <div className="absolute inset-0 noise pointer-events-none" aria-hidden="true" />
          <div className="relative z-10 max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 reveal-scale">
            <div className="text-center glass p-8 sm:p-12 lg:p-16 rounded-2xl sm:rounded-3xl border border-primary/20 relative overflow-hidden">
              <div className="absolute -top-24 -left-24 w-48 sm:w-64 h-48 sm:h-64 bg-primary/15 blur-[120px] rounded-full pointer-events-none" aria-hidden="true" />
              <div className="absolute -bottom-24 -right-24 w-48 sm:w-64 h-48 sm:h-64 bg-secondary/15 blur-[120px] rounded-full pointer-events-none" aria-hidden="true" />
              <h2 className="font-headline font-extrabold text-2xl sm:text-3xl lg:text-4xl xl:text-5xl mb-4 sm:mb-6 relative z-10 tracking-tight leading-tight text-on-surface">
                Ready to automate your <span className="text-primary neon-text">voice layer</span>?
              </h2>
              <p className="text-on-surface-variant text-sm sm:text-base lg:text-lg mb-8 sm:mb-10 relative z-10 max-w-xl mx-auto font-body">
                Join the next generation of operational efficiency. Seamless integration with your existing CRM and tech stack.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center relative z-10">
                <Link
                  href="/sign-up"
                  className="group inline-flex items-center justify-center gap-2 bg-primary text-on-primary px-6 sm:px-10 py-3 sm:py-5 font-headline font-bold rounded-xl transition-all duration-300 hover:shadow-[0_0_30px_rgba(255,45,120,0.5)] hover:scale-[1.03] active:scale-95 text-sm sm:text-base"
                >
                  Start Your Free Pilot
                  <span className="material-symbols-outlined group-hover:translate-x-1 transition-transform">
                    arrow_forward
                  </span>
                </Link>
                <Link
                  href="/pricing"
                  className="inline-flex items-center justify-center gap-2 bg-surface-variant text-on-surface px-6 sm:px-10 py-3 sm:py-5 font-headline font-bold rounded-xl hover:bg-surface-container-highest transition-all duration-300 active:scale-95 text-sm sm:text-base border border-outline-variant/20"
                >
                  View Pricing Options
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}
