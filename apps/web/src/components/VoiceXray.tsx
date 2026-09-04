"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { clampMs, getActiveLayerIndex } from "@/lib/voiceXray";

export interface LayerData {
  id: string;
  hopMs: number;
  stepRange: [number, number];
  label: string;
  system: string;
  accent: string;
  status: string;
  summary: string;
  payload: string;
  metadata: { label: string; value: string }[];
}

export const XRAY_LAYERS: LayerData[] = [
  {
    id: "01",
    hopMs: 42,
    stepRange: [0, 84],
    label: "RAW PCM INGRESS",
    system: "UK Edge // VAD Ingress (eu-west-2)",
    accent: "#5EEAD4",
    status: "STREAMING AUDIO",
    summary: "High-fidelity acoustic stream ingested at edge with instant speech activity detection.",
    payload: "sample_rate: 16000Hz \u00b7 channels: 1 \u00b7 packet_loss: 0.00% \u00b7 jitter: 1.2ms \u00b7 protocol: WebRTC-Opus",
    metadata: [
      { label: "Edge Gateway", value: "London (eu-west-2)" },
      { label: "VAD Latency", value: "12ms" },
      { label: "Signal SNR", value: "+38 dB" },
      { label: "Format", value: "16kHz PCM" },
    ],
  },
  {
    id: "02",
    hopMs: 84,
    stepRange: [84, 112],
    label: "WHISPER STT TOKENS",
    system: "Neural Streaming Transcriber",
    accent: "#5EEAD4",
    status: "PHONETIC MATCH",
    summary: "Continuous phoneme-to-token inference with British UK & Hindi/Hinglish dialect resilience.",
    payload: '"Driver 204 bay 4 clear 26 pallets" \u00b7 confidence: 0.984 \u00b7 language: en-GB / hinglish \u00b7 token_rate: 48 tok/s',
    metadata: [
      { label: "Hop 1 Latency", value: "84ms" },
      { label: "Acoustic Model", value: "Whisper Turbo" },
      { label: "Confidence", value: "98.4%" },
      { label: "Dialect Match", value: "UK Logistics" },
    ],
  },
  {
    id: "03",
    hopMs: 112,
    stepRange: [112, 196],
    label: "INTENT MATRIX",
    system: "Operational Logic Engine",
    accent: "#5EEAD4",
    status: "INTENT RESOLVED",
    summary: "Extracts logistics parameters, validates depot capacity, and checks driver authorization.",
    payload: 'intent: "dock_clearance_and_stock_check" \u00b7 entity_slot: "Bay 4" \u00b7 cargo_units: 26 \u00b7 pin_verified: true',
    metadata: [
      { label: "Hop 2 Latency", value: "112ms" },
      { label: "Resolution", value: "dock_clearance" },
      { label: "Auth Check", value: "Verified (PIN 8841)" },
      { label: "Guardrail SLA", value: "Pass (< 30ms)" },
    ],
  },
  {
    id: "04",
    hopMs: 196,
    stepRange: [196, 196],
    label: "LIVE TOOL MUTATION",
    system: "Google Sheets & ERP Roster Mirror",
    accent: "#5EEAD4",
    status: "TRANSACTION COMMITTED",
    summary: "Deterministic execution updates the live dock roster and ERP before the driver finishes speaking.",
    payload: 'action: "sheets.updateRow" \u00b7 range: "Bays!D4:F4" \u00b7 values: ["ALLOCATED", "Driver 204", "26 Pallets"] \u2192 200 OK',
    metadata: [
      { label: "Glass-to-Glass", value: "196ms Turn" },
      { label: "Tool Commit", value: "Google Sheets API" },
      { label: "Sync Status", value: "200 OK (0 retries)" },
      { label: "Audit Hash", value: "sha256:7f8a92e1" },
    ],
  },
];

function WaveformVisualizer({ progress, active }: { progress: number; active: boolean }) {
  const bars = 42;
  return (
    <div className="flex items-center justify-between gap-[2px] sm:gap-1 h-8 w-full px-2" aria-hidden="true">
      {Array.from({ length: bars }).map((_, i) => {
        const barPos = (i / bars) * 196;
        const isPassed = barPos <= progress;
        const heightPct = Math.round(20 + Math.sin(i * 0.45) * 35 + ((i * 19) % 40));
        return (
          <div
            key={i}
            className="flex-1 rounded-full transition-all duration-150"
            style={{
              height: `${Math.min(100, Math.max(15, heightPct))}%`,
              backgroundColor: isPassed && active ? "#5EEAD4" : "rgba(255, 255, 255, 0.12)",
              boxShadow: isPassed && active ? "0 0 8px rgba(94, 234, 212, 0.4)" : "none",
            }}
          />
        );
      })}
    </div>
  );
}

export default function VoiceXray() {
  const [msProgress, setMsProgress] = useState<number>(112);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const sectionRef = useRef<HTMLElement | null>(null);
  const pinContainerRef = useRef<HTMLDivElement | null>(null);
  const trackRef = useRef<HTMLDivElement | null>(null);
  const draggingRef = useRef(false);

  const activeLayerIndex = getActiveLayerIndex(msProgress);
  const activeLayer = XRAY_LAYERS[activeLayerIndex];

  // reduced-motion -> static last frame (no pin, no play)
  useEffect(() => {
    if (typeof window === "undefined") return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const apply = () => {
      const rm = mq.matches;
      setReducedMotion(rm);
      if (rm) {
        setMsProgress(196);
        setIsPlaying(false);
      }
    };
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  // GSAP Desktop Pinning (disabled on mobile and reduced-motion)
  useEffect(() => {
    if (typeof window === "undefined") return;
    gsap.registerPlugin(ScrollTrigger);
    const isDesktop = window.innerWidth >= 1024;
    if (reducedMotion || !isDesktop || !sectionRef.current || !pinContainerRef.current) return;
    const trigger = ScrollTrigger.create({
      trigger: sectionRef.current,
      start: "top top",
      end: "+=1200",
      pin: pinContainerRef.current,
      anticipatePin: 1,
      scrub: 0.6,
      onUpdate: (self) => setMsProgress(clampMs(self.progress * 196)),
    });
    return () => trigger.kill();
  }, [reducedMotion]);

  // Keyboard
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (reducedMotion && (e.key === "ArrowLeft" || e.key === "ArrowRight" || e.key === "ArrowUp" || e.key === "ArrowDown")) return;
    if (e.key === "ArrowLeft" || e.key === "ArrowDown") {
      e.preventDefault();
      setMsProgress((prev) => clampMs(prev - 4));
    } else if (e.key === "ArrowRight" || e.key === "ArrowUp") {
      e.preventDefault();
      setMsProgress((prev) => clampMs(prev + 4));
    } else if (e.key === "Home") {
      e.preventDefault();
      setMsProgress(0);
    } else if (e.key === "End") {
      e.preventDefault();
      setMsProgress(196);
    }
  };

  // Play loop (disabled under reduced-motion)
  useEffect(() => {
    if (!isPlaying || reducedMotion) return;
    const interval = setInterval(() => {
      setMsProgress((prev) => {
        if (prev >= 196) {
          setIsPlaying(false);
          return 196;
        }
        return clampMs(prev + 2);
      });
    }, 16);
    return () => clearInterval(interval);
  }, [isPlaying, reducedMotion]);

  // drag helpers — pointer unifies mouse + touch + pen
  const updateFromClientX = useCallback((clientX: number) => {
    const el = trackRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    if (rect.width === 0) return;
    const ratio = (clientX - rect.left) / rect.width;
    setMsProgress(clampMs(ratio * 196));
  }, []);

  const onPointerDown = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (reducedMotion) return;
      draggingRef.current = true;
      (e.currentTarget as HTMLDivElement).setPointerCapture(e.pointerId);
      updateFromClientX(e.clientX);
      // keep single focusable slider: move focus to the range input
      (trackRef.current?.querySelector('input[type="range"]') as HTMLElement | null)?.focus();
      e.preventDefault();
    },
    [reducedMotion, updateFromClientX]
  );

  const onPointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (!draggingRef.current || reducedMotion) return;
      updateFromClientX(e.clientX);
    },
    [reducedMotion, updateFromClientX]
  );

  const onPointerUp = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    draggingRef.current = false;
    try {
      (e.currentTarget as HTMLDivElement).releasePointerCapture(e.pointerId);
    } catch {}
  }, []);

  return (
    <section
      ref={sectionRef}
      id="section-04"
      data-section="04"
      aria-label="04 // Voice X-ray"
      className="relative w-full border-t border-white/[0.06] bg-[#030308] text-white py-12 lg:py-0 lg:min-h-[140vh]"
    >
      {/* Anchor alias so both #section-04 and #voice-xray land on Voice X-ray */}
      <span id="voice-xray" className="absolute -top-28 pointer-events-none" aria-hidden="true" />
      <div
        ref={pinContainerRef}
        className="w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 min-h-[100svh] flex flex-col justify-center pt-20 sm:pt-24 pb-4 sm:pb-6"
      >
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-3 sm:mb-4 lg:mb-5">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-0.5 rounded-full border border-[#5EEAD4]/30 bg-[#5EEAD4]/[0.06] text-[11px] font-mono tracking-widest text-[#5EEAD4] uppercase mb-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-[#5EEAD4] animate-pulse" />
              04 / 08 • Telemetry // Voice X-Ray Engine
            </div>
            <h2 className="font-headline font-black text-2xl sm:text-3xl lg:text-4xl tracking-tight text-white leading-tight">
              Hear the signal. <span className="text-white/60">See every decision.</span>
            </h2>
          </div>
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-lg border border-white/[0.1] bg-white/[0.03] font-mono text-[11px] text-white/70">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
              DEMO REPLAY // CALL #8841
            </div>
            <button
              type="button"
              onClick={() => {
                if (reducedMotion) {
                  setMsProgress(196);
                  setIsPlaying(false);
                  return;
                }
                setMsProgress(0);
                setIsPlaying(true);
              }}
              className="inline-flex items-center gap-1.5 px-3.5 py-1 rounded-lg border border-[#5EEAD4]/40 bg-[#5EEAD4]/10 hover:bg-[#5EEAD4]/20 text-[#5EEAD4] font-mono text-xs font-bold transition-colors cursor-pointer"
            >
              <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
              {isPlaying ? "Replaying..." : "Replay 196ms Turn"}
            </button>
          </div>
        </div>

        <div
          aria-label="Voice X-ray console"
          className="relative w-full rounded-2xl sm:rounded-3xl border border-white/[0.1] bg-[#030308]/95 backdrop-blur-2xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.08),0_20px_50px_rgba(0,0,0,0.85)] overflow-hidden"
        >
          {/* Header Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 px-4 sm:px-6 py-2.5 sm:py-3 border-b border-white/[0.08] bg-white/[0.02]">
            <div className="flex items-center gap-2.5 font-mono text-[11px] sm:text-xs text-white/80">
              <span className="h-1.5 w-1.5 rounded-full bg-[#5EEAD4]" />
              <span className="font-bold tracking-wider text-white">UK EDGE HOP TRACE</span>
              <span className="text-white/40">|</span>
              <span className="text-[#5EEAD4]">~200ms Turn Target</span>
            </div>
            <div className="flex items-center gap-1.5 sm:gap-2 font-mono text-xs">
              <span className="text-white/40 text-[10px] hidden sm:inline mr-1">Hop Milestones:</span>
              <button
                type="button"
                id="btn-milestone-84"
                onClick={() => {
                  setIsPlaying(false);
                  setMsProgress(84);
                }}
                className={`px-2 py-0.5 sm:px-2.5 sm:py-1 rounded-md text-[11px] border transition-all cursor-pointer ${
                  activeLayerIndex === 1
                    ? "border-[#5EEAD4] bg-[#5EEAD4]/15 text-[#5EEAD4] font-bold shadow-[0_0_10px_rgba(94,234,212,0.3)]"
                    : "border-white/[0.08] bg-white/[0.02] text-white/60 hover:text-white"
                }`}
              >
                84ms STT
              </button>
              <button
                type="button"
                id="btn-milestone-112"
                onClick={() => {
                  setIsPlaying(false);
                  setMsProgress(112);
                }}
                className={`px-2 py-0.5 sm:px-2.5 sm:py-1 rounded-md text-[11px] border transition-all cursor-pointer ${
                  activeLayerIndex === 2
                    ? "border-[#5EEAD4] bg-[#5EEAD4]/15 text-[#5EEAD4] font-bold shadow-[0_0_10px_rgba(94,234,212,0.3)]"
                    : "border-white/[0.08] bg-white/[0.02] text-white/60 hover:text-white"
                }`}
              >
                112ms Intent
              </button>
              <button
                type="button"
                id="btn-milestone-196"
                onClick={() => {
                  setIsPlaying(false);
                  setMsProgress(196);
                }}
                className={`px-2 py-0.5 sm:px-2.5 sm:py-1 rounded-md text-[11px] border transition-all cursor-pointer ${
                  activeLayerIndex === 3
                    ? "border-[#5EEAD4] bg-[#5EEAD4]/15 text-[#5EEAD4] font-bold shadow-[0_0_10px_rgba(94,234,212,0.3)]"
                    : "border-white/[0.08] bg-white/[0.02] text-white/60 hover:text-white"
                }`}
              >
                196ms Write
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-5 p-4 sm:p-5 lg:p-6">
            <div className="lg:col-span-7 flex flex-col justify-between space-y-3 sm:space-y-4">
              <div className="flex items-center justify-between font-mono text-xs text-white/60 pb-1.5 border-b border-white/[0.04]">
                <div className="flex items-center gap-2">
                  <span className="text-[#5EEAD4] font-bold text-sm">{msProgress} ms</span>
                  <span className="text-white/30">/ 196ms total turn</span>
                </div>
                <div className="text-[10px] uppercase tracking-wider text-white/40">Keyboard: ← / → Arrow Keys</div>
              </div>

              <div className="space-y-1.5 sm:space-y-2">
                {XRAY_LAYERS.map((layer, idx) => {
                  const isActive = idx <= activeLayerIndex;
                  const isCurrent = idx === activeLayerIndex;
                  return (
                    <div
                      key={layer.id}
                      onClick={() => setMsProgress(layer.hopMs)}
                      className={`group relative p-2.5 sm:p-3 rounded-xl border transition-all duration-200 cursor-pointer ${isCurrent ? "border-[#5EEAD4]/60 bg-[#5EEAD4]/[0.06] shadow-[0_0_16px_rgba(94,234,212,0.12)]" : isActive ? "border-white/[0.10] bg-white/[0.02]" : "border-white/[0.04] bg-transparent opacity-40 hover:opacity-75"}`}
                    >
                      <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-2">
                          <span className={`font-mono text-[9px] px-1.5 py-0.5 rounded font-bold ${isCurrent ? "bg-[#5EEAD4] text-[#030308]" : "bg-white/[0.06] text-white/70"}`}>LAYER {layer.id}</span>
                          <span className="font-headline font-bold text-xs sm:text-sm text-white tracking-wide">{layer.label}</span>
                        </div>
                        <span className={`font-mono text-[11px] font-semibold ${isActive ? "text-[#5EEAD4]" : "text-white/40"}`}>{idx === 0 ? "0–56ms" : idx === 1 ? "84ms" : idx === 2 ? "112ms" : "196ms"}</span>
                      </div>
                      <div className="relative h-5 sm:h-6 w-full rounded-md bg-[#030308] border border-white/[0.06] overflow-hidden flex items-center">
                        <WaveformVisualizer progress={Math.max(0, msProgress - (idx === 0 ? 0 : XRAY_LAYERS[idx - 1].hopMs))} active={isActive} />
                        <div className="absolute inset-y-0 w-0.5 bg-[#5EEAD4] shadow-[0_0_10px_#5EEAD4] transition-all duration-75" style={{ left: `${Math.min(100, Math.max(0, (msProgress / 196) * 100))}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Drag scrubber — fully visible, high contrast, non-clipped */}
              <div className="pt-1.5">
                <div
                  ref={trackRef}
                  onPointerDown={onPointerDown}
                  onPointerMove={onPointerMove}
                  onPointerUp={onPointerUp}
                  className="relative flex items-center py-2 select-none cursor-pointer"
                  style={{ touchAction: "none" }}
                >
                  <input
                    id="voice-xray-scrubber"
                    type="range"
                    role="slider"
                    min="0"
                    max="196"
                    value={msProgress}
                    onChange={(e) => !reducedMotion && setMsProgress(clampMs(Number(e.target.value)))}
                    onKeyDown={handleKeyDown}
                    disabled={reducedMotion}
                    aria-label="Voice X-ray millisecond scrubber (use Left and Right arrow keys to scrub)"
                    aria-valuemin={0}
                    aria-valuemax={196}
                    aria-valuenow={msProgress}
                    aria-valuetext={`${msProgress}ms hop - ${activeLayer.label}`}
                    className="w-full h-2 bg-white/[0.12] rounded-lg appearance-none cursor-pointer accent-[#5EEAD4] focus:outline-none focus:ring-2 focus:ring-[#5EEAD4]/50 disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{ touchAction: "none" }}
                  />
                </div>
                <div className="flex justify-between font-mono text-[10px] sm:text-[11px] text-white/50 mt-1.5 px-1">
                  <span className={activeLayerIndex === 0 ? "text-[#5EEAD4] font-bold" : "text-white/40"}>0ms (Ingress)</span>
                  <span className={activeLayerIndex === 1 ? "text-[#5EEAD4] font-bold" : "text-white/40"}>84ms (STT)</span>
                  <span className={activeLayerIndex === 2 ? "text-[#5EEAD4] font-bold" : "text-white/40"}>112ms (Intent)</span>
                  <span className={activeLayerIndex === 3 ? "text-[#5EEAD4] font-bold" : "text-white/40"}>196ms (Tool Write)</span>
                </div>
              </div>
            </div>

            {/* Right column — live telemetry & SLA */}
            <div className="lg:col-span-5 flex flex-col justify-between border-t lg:border-t-0 lg:border-l border-white/[0.08] pt-4 lg:pt-0 lg:pl-5">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono text-[10px] uppercase tracking-wider text-white/50">Live Telemetry // Layer {activeLayer.id}</span>
                  <span className="px-2 py-0.5 rounded-full font-mono text-[9px] font-bold bg-[#5EEAD4]/10 border border-[#5EEAD4]/30 text-[#5EEAD4]">{activeLayer.status}</span>
                </div>
                <h3 className="font-headline font-bold text-lg sm:text-xl text-white mb-0.5">{activeLayer.label}</h3>
                <p className="font-mono text-[11px] text-[#5EEAD4]/80 mb-2">{activeLayer.system}</p>
                <p className="font-sans text-xs sm:text-sm text-white/70 leading-relaxed mb-3">{activeLayer.summary}</p>
                <div className="p-2.5 sm:p-3 rounded-xl bg-[#030308] border border-white/[0.08] font-mono text-[11px] text-white/90 mb-3 shadow-inner">
                  <div className="text-[9px] uppercase tracking-wider text-white/40 mb-1.5 border-b border-white/[0.06] pb-1 flex justify-between">
                    <span>Decoded Payload</span>
                    <span className="text-[#5EEAD4]">t = +{msProgress}ms</span>
                  </div>
                  <code className="text-[#5EEAD4]/90 break-all leading-relaxed block">{activeLayer.payload}</code>
                </div>
                <div className="grid grid-cols-2 gap-2 mb-3">
                  {activeLayer.metadata.map((meta, i) => (
                    <div key={i} className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                      <span className="block font-mono text-[9px] text-white/40 uppercase tracking-wider mb-0.5">{meta.label}</span>
                      <span className="font-headline font-bold text-xs sm:text-sm text-white">{meta.value}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="p-2.5 sm:p-3 rounded-xl border border-emerald-500/20 bg-emerald-500/[0.04] flex items-center justify-between mt-auto">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="font-mono text-[11px] sm:text-xs font-bold text-white">
                    Glass-to-Glass: &lt; 200ms | PASS ({msProgress}ms)
                  </span>
                </div>
                <span className="font-mono text-[10px] sm:text-xs text-emerald-400 font-bold">
                  SLA VERIFIED
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
