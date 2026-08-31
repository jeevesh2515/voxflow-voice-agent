"use client";

import { useState } from "react";

const hubs = [
  { name: "London Central", code: "LDN / 01", phone: "+44 20 •••• 0821", state: "SPEAKING", color: "#ff2d78", level: 82 },
  { name: "Birmingham Hub", code: "BHM / 02", phone: "+44 121 •••• 4431", state: "LISTENING", color: "#00ffcc", level: 55 },
  { name: "Manchester Express", code: "MAN / 03", phone: "+44 161 •••• 7118", state: "TOOL_CALL", color: "#c6ff00", level: 73 },
  { name: "Bristol Fleet", code: "BRS / 04", phone: "+44 117 •••• 3190", state: "LISTENING", color: "#00ffcc", level: 38 },
  { name: "Leeds Gateway", code: "LDS / 05", phone: "+44 113 •••• 8812", state: "SPEAKING", color: "#ff2d78", level: 64 },
  { name: "Glasgow Freight", code: "GLA / 06", phone: "+44 141 •••• 4420", state: "ESCALATION", color: "#ffe04a", level: 29 },
];

export default function DispatchSwitchboard() {
  const [activeHub, setActiveHub] = useState(0);
  const hub = hubs[activeHub];

  return (
    <section className="relative py-28 sm:py-40" id="switchboard">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid gap-10 lg:grid-cols-[0.72fr_1.28fr] lg:items-end lg:gap-20">
          <div>
            <span className="font-label text-[10px] uppercase tracking-[0.25em] text-[#ff2d78]">04 — Multi-depot switchboard</span>
            <h2 className="mt-4 font-headline text-4xl font-extrabold leading-[0.98] tracking-[-0.055em] text-white sm:text-6xl">
              Six hubs.
              <br />
              <span className="text-[#66757e]">One signal.</span>
            </h2>
            <p className="mt-5 max-w-sm font-body text-base leading-7 text-[#9ba8b5]">Monitor every concurrent AI dispatch line across the UK, without adding another screen for your team to babysit.</p>
            <div className="mt-8 border-l border-[#ff2d78]/60 pl-4">
              <span className="font-label text-[9px] uppercase tracking-[0.18em] text-[#71808a]">Focused route</span>
              <p className="mt-2 font-headline text-lg font-bold text-white">{hub.name}</p>
              <p className="mt-1 font-label text-[10px] uppercase tracking-[0.12em]" style={{ color: hub.color }}>{hub.state} / {hub.code}</p>
            </div>
          </div>

          <div className="switchboard-shell">
            <div className="switchboard-core">
              <div className="flex items-center justify-between border-b border-white/[0.08] px-5 py-4 sm:px-7">
                <span className="font-label text-[10px] uppercase tracking-[0.2em] text-white">VoxFlow / dispatch control</span>
                <span className="flex items-center gap-2 font-label text-[9px] uppercase tracking-[0.15em] text-[#00ffcc]"><span className="h-1.5 w-1.5 rounded-full bg-[#00ffcc]" /> 06 channels online</span>
              </div>
              <div className="grid gap-px bg-white/[0.07] sm:grid-cols-2">
                {hubs.map((item, index) => (
                  <button key={item.code} type="button" className={`switchboard-card text-left ${activeHub === index ? "switchboard-card-active" : ""}`} onMouseEnter={() => setActiveHub(index)} onFocus={() => setActiveHub(index)} onClick={() => setActiveHub(index)}>
                    <div className="flex items-start justify-between gap-4">
                      <div><span className="font-label text-[9px] uppercase tracking-[0.17em] text-[#6d7b84]">{item.code}</span><h3 className="mt-2 font-headline text-base font-bold text-white">{item.name}</h3></div>
                      <span className="mt-1 h-2 w-2 rounded-full" style={{ backgroundColor: item.color, boxShadow: `0 0 12px ${item.color}` }} />
                    </div>
                    <p className="mt-3 font-mono text-[11px] text-[#8c9aa2]">{item.phone}</p>
                    <div className="mt-5 flex h-7 items-end gap-1">
                      {Array.from({ length: 18 }, (_, bar) => <span key={bar} className={`switchboard-bar ${item.state === "SPEAKING" ? "switchboard-bar-active" : ""}`} style={{ height: `${Math.max(12, (item.level + bar * 7) % 86)}%`, backgroundColor: item.color, animationDelay: `${bar * 28}ms` }} />)}
                    </div>
                    <div className="mt-4 flex items-center justify-between border-t border-white/[0.07] pt-3 font-label text-[9px] uppercase tracking-[0.14em]"><span style={{ color: item.color }}>{item.state}</span><span className="text-[#66757e]">{index === activeHub ? "inspect ↗" : "standby"}</span></div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
