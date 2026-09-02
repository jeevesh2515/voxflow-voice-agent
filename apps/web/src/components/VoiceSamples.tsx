"use client";

import { useState, useRef, useEffect } from "react";

export type VoiceSample = {
  id: string;
  lang: string;
  langCode: string;
  badge: string;
  scenario: string;
  callerAudioText: string;
  callerLabel: string;
  agentResponseText: string;
  agentLabel: string;
  turnLatency: string;
  intentTag: string;
};

const SAMPLES: VoiceSample[] = [
  {
    id: "en-uk",
    lang: "UK English",
    langCode: "en-GB",
    badge: "UK Edge · London DID",
    scenario: "M4 Corridor Depot Check-in",
    callerLabel: "Driver (Bristol Fleet)",
    callerAudioText: "Driver checking in for Bay 4 with 22 pallets from Manchester depot.",
    agentLabel: "Voxflow Agent (eu-west-2)",
    agentResponseText: "Confirmed. Bay 4 is clear. Manifest logged and sheet updated.",
    turnLatency: "192ms",
    intentTag: "dock_reassignment // PASS",
  },
  {
    id: "hi",
    lang: "Hindi (हिंदी)",
    langCode: "hi-IN",
    badge: "Bilingual Edge · Multi-Depot",
    scenario: "ड्राइवर चेक-इन एवं डॉक आवंटन",
    callerLabel: "ड्राइवर (इनबाउंड फ्लीट)",
    callerAudioText: "नमस्ते, मैं बे 4 के लिए 22 पैलेट लेकर पहुंचा हूं।",
    agentLabel: "Voxflow एजेंट",
    agentResponseText: "नमस्ते। बे 4 खाली है, सीधे डॉक पर जाएं। शीट अपडेट कर दी गई है।",
    turnLatency: "196ms",
    intentTag: "driver_checkin_hi // PASS",
  },
  {
    id: "hinglish",
    lang: "Hinglish (Code-Switching)",
    langCode: "hi-IN",
    badge: "Real-Time Code-Switching",
    scenario: "M6 Freight Delay & Triage",
    callerLabel: "Fleet Driver",
    callerAudioText: "Gaddi M6 pe phasi hai, delivery delay ho jayegi. Slot reschedule kardo.",
    agentLabel: "Voxflow Agent",
    agentResponseText: "Slot Friday morning 08:00–11:00 me reschedule kar diya hai. ERP updated.",
    turnLatency: "198ms",
    intentTag: "reschedule_order // PASS",
  },
  {
    id: "en-us",
    lang: "US Freight",
    langCode: "en-US",
    badge: "US Freight Gateway",
    scenario: "High-Priority Express Re-Route",
    callerLabel: "Logistics Carrier",
    callerAudioText: "Need urgent dock reassignment for express trailer 8841.",
    agentLabel: "Voxflow Agent",
    agentResponseText: "Rerouting trailer 8841 to Gate 3 immediately. Priority flag committed.",
    turnLatency: "188ms",
    intentTag: "priority_reroute // PASS",
  },
];

export default function VoiceSamples() {
  const [activeId, setActiveId] = useState<string>("en-uk");
  const [playingId, setPlayingId] = useState<string | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);

  const activeSample = SAMPLES.find((s) => s.id === activeId) || SAMPLES[0];

  // Stop browser speech on unmount
  useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const handlePlay = (sample: VoiceSample) => {
    if (typeof window === "undefined") return;

    if (playingId === sample.id) {
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      setPlayingId(null);
      return;
    }

    // Cancel any ongoing playback
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
    }

    setPlayingId(sample.id);
    if (typeof window !== "undefined") window.dispatchEvent(new CustomEvent("voxflow:voice-play", { detail: { lang: sample.id } }));

    if ("speechSynthesis" in window) {
      // Speak caller then agent response with natural pause
      const utteranceCaller = new SpeechSynthesisUtterance(sample.callerAudioText);
      utteranceCaller.lang = sample.langCode;
      utteranceCaller.rate = 1.05;

      const utteranceAgent = new SpeechSynthesisUtterance(sample.agentResponseText);
      utteranceAgent.lang = sample.langCode;
      utteranceAgent.rate = 1.0;

      utteranceCaller.onend = () => {
        window.setTimeout(() => {
          window.speechSynthesis.speak(utteranceAgent);
        }, 120);
      };

      utteranceAgent.onend = () => {
        setPlayingId(null);
      };

      utteranceAgent.onerror = () => {
        setPlayingId(null);
      };
      // audio end/error already resets playingId; hero pulse decays via VoiceCoreCanvas damping

      utteranceCaller.onerror = () => {
        setPlayingId(null);
      };

      window.speechSynthesis.speak(utteranceCaller);
    } else {
      // Fallback: visual simulation for environments without Web Speech API
      setPlayingId(sample.id);
      setTimeout(() => setPlayingId(null), 3000);
    }
  };

  return (
    <div className="w-full max-w-6xl mx-auto mt-16 pt-16 border-t border-white/[0.08]">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/[0.08] bg-white/[0.02] text-xs font-mono tracking-widest text-[#5EEAD4] uppercase mb-3">
            <span className="h-1.5 w-1.5 rounded-full bg-[#5EEAD4] animate-pulse" />
            Operational Voice Demonstrations
          </div>
          <h3 className="font-headline font-black text-2xl sm:text-4xl text-white tracking-tight">
            Hear it in English. <span className="text-white/60">Hear it in Hindi.</span>
          </h3>
          <p className="font-sans text-sm text-white/70 max-w-xl mt-2 leading-relaxed">
            Listen to ~200ms turn, UK edge operations across British English, Hindi, and natural code-switching.
          </p>
        </div>

        {/* Play Active Button */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            id={`play-btn-${activeSample.id}`}
            onClick={() => handlePlay(activeSample)}
            className={`inline-flex items-center gap-2.5 px-5 py-2.5 rounded-xl font-headline font-bold text-xs transition-all shadow-lg active:scale-95 ${
              playingId === activeSample.id
                ? "bg-rose-500 text-white shadow-rose-500/30 animate-pulse"
                : "bg-[#5EEAD4] text-[#030308] hover:shadow-[0_0_20px_rgba(94,234,212,0.4)]"
            }`}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              {playingId === activeSample.id ? (
                <rect x="6" y="4" width="12" height="16" rx="2" />
              ) : (
                <polygon points="5 3 19 12 5 21 5 3" />
              )}
            </svg>
            {playingId === activeSample.id ? "Stop Sample" : `Play ${activeSample.lang} Sample`}
          </button>
        </div>
      </div>

      {/* Language Selector Pills */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5 sm:gap-3 mb-6">
        {SAMPLES.map((s) => {
          const isSelected = s.id === activeId;
          const isPlaying = s.id === playingId;
          return (
            <button
              key={s.id}
              type="button"
              id={`select-sample-${s.id}`}
              onClick={() => {
                setActiveId(s.id);
                if (playingId && playingId !== s.id) {
                  if (typeof window !== "undefined" && "speechSynthesis" in window) {
                    window.speechSynthesis.cancel();
                  }
                  setPlayingId(null);
                }
              }}
              className={`flex flex-col items-start p-3.5 rounded-2xl border text-left transition-all duration-200 ${
                isSelected
                  ? "border-[#5EEAD4]/60 bg-[#5EEAD4]/10 shadow-[0_0_20px_rgba(94,234,212,0.12)] text-white"
                  : "border-white/[0.06] bg-white/[0.02] text-white/60 hover:text-white hover:bg-white/[0.04]"
              }`}
            >
              <div className="flex items-center justify-between w-full mb-1">
                <span className="font-mono text-[10px] text-[#5EEAD4] font-bold uppercase tracking-wider">
                  {s.lang}
                </span>
                {isPlaying && (
                  <span className="flex items-center gap-0.5">
                    <span className="h-2.5 w-0.5 bg-[#5EEAD4] animate-pulse" />
                    <span className="h-4 w-0.5 bg-[#5EEAD4] animate-pulse" style={{ animationDelay: "0.15s" }} />
                    <span className="h-2 w-0.5 bg-[#5EEAD4] animate-pulse" style={{ animationDelay: "0.3s" }} />
                  </span>
                )}
              </div>
              <span className="font-headline font-bold text-xs sm:text-sm text-white truncate w-full">
                {s.scenario}
              </span>
            </button>
          );
        })}
      </div>

      {/* Live Sample Console Card */}
      <div className="rounded-3xl border border-white/[0.09] bg-[#030308]/95 backdrop-blur-2xl p-6 sm:p-8 shadow-[inset_0_1px_1px_rgba(255,255,255,0.08),0_25px_50px_rgba(0,0,0,0.85)]">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6 pb-3 border-b border-white/[0.06] font-mono text-xs">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-[#5EEAD4] animate-pulse" />
            <span className="font-bold text-white uppercase">{activeSample.scenario}</span>
            <span className="text-white/40">|</span>
            <span className="text-[#5EEAD4]">{activeSample.badge}</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-white/40">Turn Target:</span>
            <span className="text-emerald-400 font-bold">{activeSample.turnLatency} (PASS)</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Caller Dialogue */}
          <div className="p-4 sm:p-5 rounded-2xl border border-white/[0.06] bg-white/[0.02] flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-[10px] uppercase tracking-wider text-white/50">
                  {activeSample.callerLabel}
                </span>
                <span className="font-mono text-[10px] text-white/30">PCM Ingress</span>
              </div>
              <p className="font-sans text-sm sm:text-base text-white/90 leading-relaxed italic">
                “{activeSample.callerAudioText}”
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-white/[0.04] flex items-center justify-between font-mono text-[10px] text-white/40">
              <span>Whisper STT Tokens</span>
              <span className="text-[#5EEAD4]">84ms</span>
            </div>
          </div>

          {/* Agent Response & Live Action */}
          <div className="p-4 sm:p-5 rounded-2xl border border-[#5EEAD4]/20 bg-[#5EEAD4]/[0.04] flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-[10px] uppercase tracking-wider text-[#5EEAD4] font-bold">
                  {activeSample.agentLabel}
                </span>
                <span className="font-mono text-[10px] text-emerald-400 font-bold">
                  {activeSample.intentTag}
                </span>
              </div>
              <p className="font-sans text-sm sm:text-base text-white leading-relaxed font-medium">
                “{activeSample.agentResponseText}”
              </p>
            </div>
            <div className="mt-4 pt-3 border-t border-white/[0.04] flex items-center justify-between font-mono text-[10px] text-white/60">
              <span>Llama Intent + Edge TTS</span>
              <span className="text-[#5EEAD4] font-bold">{activeSample.turnLatency} Turn</span>
            </div>
          </div>
        </div>

        {/* Direct Play Buttons Row */}
        <div className="flex flex-wrap items-center justify-between gap-3 mt-6 pt-4 border-t border-white/[0.06]">
          <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
            <span className="text-white/40 text-[11px] mr-1">Quick Play:</span>
            <button
              type="button"
              onClick={() => {
                setActiveId("en-uk");
                handlePlay(SAMPLES[0]);
              }}
              className="px-3 py-1 rounded-lg border border-white/[0.08] bg-white/[0.02] text-white/70 hover:text-white hover:border-[#5EEAD4]/40 transition"
            >
              Play English
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveId("hi");
                handlePlay(SAMPLES[1]);
              }}
              className="px-3 py-1 rounded-lg border border-white/[0.08] bg-white/[0.02] text-white/70 hover:text-white hover:border-[#5EEAD4]/40 transition"
            >
              Play Hindi (हिंदी)
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveId("hinglish");
                handlePlay(SAMPLES[2]);
              }}
              className="px-3 py-1 rounded-lg border border-white/[0.08] bg-white/[0.02] text-white/70 hover:text-white hover:border-[#5EEAD4]/40 transition"
            >
              Play Hinglish
            </button>
          </div>

          <span className="font-mono text-[10px] text-white/35">
            Real-time TTS synthesized via Web Speech & Edge Pipeline.
          </span>
        </div>
      </div>
    </div>
  );
}
