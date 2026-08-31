"use client";

import { useState } from "react";

const layers = [
  { id: "01", label: "RAW PCM / 16KHZ", accent: "#00ffcc", value: "00:00.041", detail: "Audio waveform amplitude" },
  { id: "02", label: "WHISPER STT TOKENS", accent: "#c6ff00", value: "84ms", detail: "sku-9941 / availability / depot" },
  { id: "03", label: "LLAMA INTENT MATRIX", accent: "#ff2d78", value: "112ms", detail: "intent: stock_check · confidence: 0.98" },
  { id: "04", label: "LIVE TOOL MUTATION", accent: "#ffe04a", value: "196ms", detail: "sheets.mirror(commit) → success" },
];

function Waveform({ active }: { active: boolean }) {
  return (
    <div className="xray-waveform" aria-hidden="true">
      {Array.from({ length: 48 }, (_, index) => (
        <span key={index} className={active ? "xray-wave-active" : ""} style={{ height: `${18 + ((index * 17) % 58)}%`, animationDelay: `${index * 18}ms` }} />
      ))}
    </div>
  );
}

export default function VoiceXray() {
  const [scrub, setScrub] = useState(56);
  const activeLayer = Math.min(3, Math.floor(scrub / 25));
  const selected = layers[activeLayer];

  return (
    <section className="relative border-y border-white/[0.06] py-28 sm:py-40" id="voice-xray">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="mb-14 max-w-3xl">
          <span className="font-label text-[10px] uppercase tracking-[0.25em] text-[#c6ff00]">02 — Voice X-ray / live inspection</span>
          <h2 className="mt-4 font-headline text-4xl font-extrabold leading-[0.98] tracking-[-0.055em] text-white sm:text-6xl lg:text-7xl">
            Hear the signal.
            <br />
            <span className="text-[#64727b]">See every decision.</span>
          </h2>
          <p className="mt-5 max-w-xl font-body text-base leading-7 text-[#9ba8b5]">
            Drag through one live call to expose the acoustic, language, reasoning, and system layers moving together in the same 196ms turn.
          </p>
        </div>

        <div className="xray-shell">
          <div className="xray-core">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.08] px-5 py-4 sm:px-7">
              <div className="flex items-center gap-3">
                <span className="xray-live-dot" />
                <span className="font-label text-[10px] uppercase tracking-[0.2em] text-white">Call / #8841 / inbound</span>
              </div>
              <span className="font-label text-[10px] uppercase tracking-[0.2em] text-[#83929c]">x-ray mode / drag scrubber</span>
            </div>

            <div className="grid gap-8 p-5 sm:p-7 lg:grid-cols-[1.2fr_0.8fr] lg:gap-12">
              <div>
                <div className="relative h-72 overflow-hidden border border-white/[0.08] bg-[#050509] p-5 sm:h-80 sm:p-7">
                  <div className="absolute inset-y-0 left-0 w-1/2 bg-gradient-to-r from-[#00ffcc]/[0.04] to-transparent" style={{ width: `${scrub}%` }} />
                  <div className="relative z-10 flex h-full flex-col justify-between">
                    <div className="flex items-center justify-between font-label text-[9px] uppercase tracking-[0.18em] text-[#71808a]">
                      <span>Call timeline</span>
                      <span>00:00.000 — 00:00.196</span>
                    </div>
                    <div className="space-y-5">
                      {layers.map((layer, index) => (
                        <div key={layer.id} className="grid grid-cols-[140px_1fr] items-center gap-3 sm:grid-cols-[180px_1fr]">
                          <span className="font-label text-[9px] uppercase tracking-[0.15em]" style={{ color: index <= activeLayer ? layer.accent : "#53616b" }}>{layer.label}</span>
                          <div className="relative h-8 border-y border-white/[0.06]">
                            <Waveform active={index === 0 && index <= activeLayer} />
                            <div className="absolute inset-y-0 left-0 border-l" style={{ left: `${scrub}%`, borderColor: layer.accent, boxShadow: `0 0 16px ${layer.accent}` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="flex justify-between font-label text-[9px] text-[#53616b]"><span>0ms</span><span>64ms</span><span>128ms</span><span>196ms</span></div>
                  </div>
                  <input className="xray-range absolute inset-x-5 bottom-3 z-20 sm:inset-x-7" type="range" min="0" max="99" value={scrub} onChange={(event) => setScrub(Number(event.target.value))} aria-label="Scrub the live voice call timeline" />
                </div>
                <div className="mt-4 flex flex-wrap gap-2 font-label text-[9px] uppercase tracking-[0.14em] text-[#74828c]">
                  <span className="rounded-full border border-white/[0.08] px-3 py-1.5">pointer / {scrub}ms</span>
                  <span className="rounded-full border border-white/[0.08] px-3 py-1.5">4 layers coupled</span>
                  <span className="rounded-full border border-[#c6ff00]/30 bg-[#c6ff00]/[0.05] px-3 py-1.5 text-[#c6ff00]">trace verified</span>
                </div>
              </div>

              <div className="flex flex-col justify-between border-l border-white/[0.08] pl-0 lg:pl-8">
                <div>
                  <span className="font-label text-[9px] uppercase tracking-[0.2em] text-[#71808a]">Selected layer / {selected.id}</span>
                  <div className="mt-4 border border-white/[0.09] bg-white/[0.025] p-5" style={{ boxShadow: `inset 3px 0 0 ${selected.accent}` }}>
                    <div className="flex items-baseline justify-between gap-4">
                      <h3 className="font-headline text-lg font-bold text-white">{selected.label}</h3>
                      <span className="font-label text-sm" style={{ color: selected.accent }}>{selected.value}</span>
                    </div>
                    <p className="mt-5 font-mono text-sm leading-6 text-[#b4c0c6]">{selected.detail}</p>
                    <p className="mt-8 font-label text-[9px] uppercase tracking-[0.18em] text-[#64727b]">Holographic readout</p>
                    <div className="mt-2 flex items-center justify-between border-t border-white/[0.08] pt-3 font-label text-[10px] text-[#a6b4bd]"><span>hop integrity</span><span className="text-[#00ffcc]">100%</span></div>
                  </div>
                </div>
                <div className="mt-8 grid grid-cols-2 gap-3">
                  <div className="border border-white/[0.08] p-4"><span className="block font-label text-[9px] uppercase tracking-[0.16em] text-[#6f7e87]">Latency</span><strong className="mt-2 block font-headline text-2xl text-white">{selected.value}</strong></div>
                  <div className="border border-white/[0.08] p-4"><span className="block font-label text-[9px] uppercase tracking-[0.16em] text-[#6f7e87]">Confidence</span><strong className="mt-2 block font-headline text-2xl text-[#c6ff00]">98.4%</strong></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
