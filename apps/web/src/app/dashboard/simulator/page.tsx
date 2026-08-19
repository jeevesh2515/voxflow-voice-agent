"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Mic, MicOff, Phone, PhoneOff, Send, Volume2, Loader2 } from "lucide-react";
import { useTenant } from "@/lib/tenant-context";

type Turn = { role: "caller" | "agent"; text: string; at: number };

function getWsUrl(): string {
  if (process.env.NEXT_PUBLIC_WS_URL) return process.env.NEXT_PUBLIC_WS_URL;
  if (typeof window !== "undefined") {
    if (window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
      return "wss://voxflow-voice-agent.onrender.com";
    }
  }
  return "ws://localhost:8000";
}

export default function PhoneSimulator() {
  const { activeTenantId, activeTenant } = useTenant();
  const [connected, setConnected] = useState(false);
  const [callId, setCallId] = useState<string | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [actions, setActions] = useState<any[]>([]);
  const [recording, setRecording] = useState(false);
  const [textInput, setTextInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [language, setLanguage] = useState<"hi" | "en">("hi");
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const lastAudioRef = useRef<HTMLAudioElement | null>(null);
  const transcriptRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll transcript
  useEffect(() => {
    if (transcriptRef.current) {
      transcriptRef.current.scrollTop = transcriptRef.current.scrollHeight;
    }
  }, [turns]);

  // ---------- WebSocket lifecycle ----------

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;
    setError(null);
    const targetWs = getWsUrl();
    const ws = new WebSocket(`${targetWs}/ws/call`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      ws.send(JSON.stringify({ type: "start", language, tenant_id: activeTenantId }));
      setTurns([
        { role: "agent", text: `नमस्ते, ${activeTenant.name} में आपका स्वागत है। मैं वाणी हूँ।`, at: Date.now() },
      ]);
    };

    ws.onmessage = async (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === "ready") {
          setCallId(msg.call_id);
        } else if (msg.type === "turn") {
          setTurns((t) => [
            ...t,
            { role: "caller", text: msg.user_text, at: Date.now() },
            { role: "agent",  text: msg.agent_text, at: Date.now() },
          ]);
          setActions(msg.actions || []);
          // Play TTS audio
          if (msg.agent_audio_b64) {
            const bytes = base64ToBytes(msg.agent_audio_b64);
            const blob = new Blob([bytes.buffer as ArrayBuffer], { type: msg.agent_audio_mime || "audio/mpeg" });
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            lastAudioRef.current = audio;
            audio.play().catch(() => {});
            audio.onended = () => URL.revokeObjectURL(url);
          }
        } else if (msg.type === "info") {
          // ignore
        } else if (msg.type === "error") {
          setError(msg.message || "unknown error");
        } else if (msg.type === "ended") {
          setConnected(false);
          setCallId(null);
        }
      } catch (e) {
        console.error("ws msg parse", e);
      }
    };

    ws.onerror = () => setError("WebSocket connection failed — is the API running?");
    ws.onclose = () => {
      setConnected(false);
      setCallId(null);
    };
  }, [language, activeTenantId, activeTenant.name]);

  const disconnect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "end" }));
    }
    setTimeout(() => wsRef.current?.close(), 200);
    setConnected(false);
    setCallId(null);
  }, []);

  // ---------- Mic capture ----------

  const startMic = useCallback(async () => {
    if (!connected) connect();
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { sampleRate: 16000, channelCount: 1 } });
      mediaStreamRef.current = stream;
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
      audioCtxRef.current = ctx;
      const source = ctx.createMediaStreamSource(stream);
      const processor = ctx.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;
      source.connect(processor);
      processor.connect(ctx.destination);

      let silentMs = 0;
      const SILENT_THRESHOLD = 0.01;
      const COMMIT_AFTER_MS = 700;
      const FRAME_MS = 50;
      const FRAMES_PER_COMMIT = Math.ceil(COMMIT_AFTER_MS / FRAME_MS);

      processor.onaudioprocess = (e) => {
        const input = e.inputBuffer.getChannelData(0);
        // Convert float32 to int16 PCM
        const pcm = new Int16Array(input.length);
        let sum = 0;
        for (let i = 0; i < input.length; i++) {
          const s = Math.max(-1, Math.min(1, input[i]));
          pcm[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          sum += Math.abs(s);
        }
        const avg = sum / input.length;
        const bytes = new Uint8Array(pcm.buffer);
        const b64 = bytesToBase64(bytes);

        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: "pcm", data: b64 }));
        }

        // Simple silence detection -> auto-commit
        if (avg < SILENT_THRESHOLD) {
          silentMs += FRAME_MS;
          if (silentMs >= COMMIT_AFTER_MS && (audioCtxRef.current as any)._lastCommit !== performance.now()) {
            (audioCtxRef.current as any)._lastCommit = performance.now();
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify({ type: "commit" }));
            }
            silentMs = 0;
          }
        } else {
          silentMs = 0;
        }
      };

      setRecording(true);
    } catch (e: any) {
      setError(`Microphone access failed: ${e.message}`);
    }
  }, [connected, connect]);

  const stopMic = useCallback(() => {
    processorRef.current?.disconnect();
    processorRef.current = null;
    mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
    mediaStreamRef.current = null;
    audioCtxRef.current?.close();
    audioCtxRef.current = null;
    setRecording(false);
    // Final commit
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "commit" }));
    }
  }, []);

  // ---------- Text input (fallback) ----------

  const sendText = useCallback(async () => {
    const text = textInput.trim();
    if (!text) return;
    setBusy(true);
    setTextInput("");
    try {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        connect();
        // small wait for handshake
        await new Promise((r) => setTimeout(r, 250));
      }
      wsRef.current?.send(JSON.stringify({ type: "text", text }));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }, [textInput, connect]);

  // ---------- Manual commit (for testing) ----------

  const manualCommit = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "commit" }));
    }
  }, []);

  // Cleanup
  useEffect(() => () => {
    processorRef.current?.disconnect();
    mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
    audioCtxRef.current?.close();
    wsRef.current?.close();
  }, []);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Header */}
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-[#12121e] p-6 rounded-2xl border border-[#242436] shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-mono text-[#94a3b8]">
            <span>Voice Lab</span>
            <span>/</span>
            <span className="text-[#00ffcc] font-bold">{activeTenant.name}</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-headline font-bold text-white tracking-tight">
            Voice Agent Phone Simulator
          </h1>
          <p className="text-xs sm:text-sm text-[#94a3b8]">
            Browser microphone & text interaction with agent persona <strong>{activeTenant.agent_name || "Vaani"}</strong> in Hindi or English.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-[#00ffcc]/10 text-[#00ffcc] border border-[#00ffcc]/30">
            <span className={`w-2 h-2 rounded-full ${connected ? "bg-[#00ffcc] animate-pulse" : "bg-[#64748b]"}`} />
            {connected ? "WebSocket Connected" : "Ready"}
          </span>
        </div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6">
        {/* Left: Phone Controller */}
        <div className="space-y-4">
          <div className="bg-[#141422] border border-[#28283c] rounded-2xl p-6 shadow-sm space-y-6">
            <div className="text-center space-y-1.5 pb-4 border-b border-[#242436]">
              <div className="w-16 h-16 rounded-2xl bg-[#ff2d78]/15 border border-[#ff2d78]/30 mx-auto flex items-center justify-center text-[#ff2d78] shadow-md">
                <Phone size={26} />
              </div>
              <h3 className="text-base font-headline font-bold text-white pt-2">{activeTenant.agent_name || "Vaani"}</h3>
              <p className="text-xs font-mono text-[#94a3b8]">VoxFlow AI Voice Agent</p>
            </div>

            {/* Language & Manual Commit Controls */}
            <div className="grid grid-cols-3 gap-2">
              <button
                onClick={() => setLanguage("hi")}
                className={`py-2 rounded-xl text-xs font-mono font-bold uppercase transition-all ${
                  language === "hi"
                    ? "bg-[#ff2d78] text-white shadow-sm"
                    : "bg-[#181826] text-[#94a3b8] hover:text-white border border-[#2c2c40]"
                }`}
              >
                हिन्दी
              </button>
              <button
                onClick={() => setLanguage("en")}
                className={`py-2 rounded-xl text-xs font-mono font-bold uppercase transition-all ${
                  language === "en"
                    ? "bg-[#ff2d78] text-white shadow-sm"
                    : "bg-[#181826] text-[#94a3b8] hover:text-white border border-[#2c2c40]"
                }`}
              >
                English
              </button>
              <button
                onClick={manualCommit}
                className="py-2 rounded-xl text-xs font-mono text-[#cbd5e1] bg-[#181826] hover:bg-[#202034] border border-[#2c2c40] hover:text-white transition-colors"
                title="Send buffered audio to STT now"
              >
                Commit
              </button>
            </div>

            {/* Call Action Buttons */}
            <div className="flex items-center justify-center gap-4 py-2">
              {!connected ? (
                <button
                  onClick={() => connect()}
                  className="h-14 w-14 rounded-2xl bg-[#00ffcc] hover:bg-[#00e6b8] flex items-center justify-center text-[#0a0a12] shadow-lg active:scale-95 transition-all"
                  aria-label="Start call"
                  title="Start Voice Session"
                >
                  <Phone size={22} />
                </button>
              ) : (
                <button
                  onClick={disconnect}
                  className="h-14 w-14 rounded-2xl bg-red-500 hover:bg-red-600 flex items-center justify-center text-white shadow-lg active:scale-95 transition-all"
                  aria-label="End call"
                  title="End Voice Session"
                >
                  <PhoneOff size={22} />
                </button>
              )}
              <button
                onClick={recording ? stopMic : startMic}
                disabled={!connected}
                className={`h-14 w-14 rounded-2xl flex items-center justify-center border transition-all active:scale-95 ${
                  recording
                    ? "bg-red-500/20 border-red-500 text-red-400 shadow-md"
                    : "bg-[#181826] border-[#2c2c40] text-white hover:border-[#ff2d78]"
                } disabled:opacity-40`}
                aria-label={recording ? "Stop mic" : "Start mic"}
                title={recording ? "Stop Microphone" : "Speak into Microphone"}
              >
                {recording ? <MicOff size={22} /> : <Mic size={22} />}
              </button>
            </div>

            {/* Audio Waveform Indicator */}
            {recording && (
              <div className="flex items-center justify-center gap-1.5 py-1">
                <span className="w-1.5 h-6 bg-[#00ffcc] rounded-full animate-bounce" />
                <span className="w-1.5 h-10 bg-[#00ffcc] rounded-full animate-bounce [animation-delay:0.15s]" />
                <span className="w-1.5 h-4 bg-[#00ffcc] rounded-full animate-bounce [animation-delay:0.3s]" />
                <span className="w-1.5 h-8 bg-[#00ffcc] rounded-full animate-bounce [animation-delay:0.45s]" />
              </div>
            )}

            <div className="text-center text-[11px] font-mono text-[#64748b]">
              {callId ? `Session ID: #${callId.slice(0, 14)}…` : "Click Call or Type below to begin"}
            </div>
          </div>

          {/* Text Input & Quick Prompts */}
          <div className="bg-[#141422] border border-[#28283c] rounded-2xl p-5 shadow-sm space-y-3">
            <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block">
              Quick Test Prompts
            </label>
            <div className="flex flex-wrap gap-1.5">
              {[
                "Check stock of cartons",
                "Track shipment SHIP-001",
                "स्टॉक चेक करो",
                "Order 20 boxes with PIN 1234",
              ].map((p) => (
                <button
                  key={p}
                  onClick={() => {
                    setTextInput(p);
                  }}
                  className="px-2.5 py-1 rounded-lg text-[11px] font-mono bg-[#181826] hover:bg-[#202034] text-[#cbd5e1] hover:text-white border border-[#2c2c40] transition-colors"
                >
                  {p}
                </button>
              ))}
            </div>

            <div className="flex gap-2 pt-1">
              <input
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendText()}
                placeholder="Type query in Hindi or English..."
                className="flex-1 bg-[#10101a] border border-[#28283c] rounded-xl px-3 py-2 text-xs text-white placeholder:text-[#64748b] focus:outline-none focus:border-[#ff2d78]"
              />
              <button
                onClick={sendText}
                disabled={busy || !textInput.trim()}
                className="px-3.5 rounded-xl bg-[#ff2d78] hover:bg-[#e02669] disabled:opacity-40 text-white font-bold transition-colors"
                aria-label="Send"
              >
                {busy ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
              </button>
            </div>

            {error && (
              <div className="text-xs text-red-400 border border-red-500/30 bg-red-500/10 rounded-xl p-2.5">
                {error}
              </div>
            )}
          </div>
        </div>

        {/* Right: Live Transcript & Tool Execution Trace */}
        <div className="bg-[#141422] border border-[#28283c] rounded-2xl flex flex-col min-h-[500px] shadow-sm overflow-hidden">
          <div className="p-4 border-b border-[#28283c] bg-[#181828] flex items-center justify-between">
            <h3 className="text-xs font-headline font-bold text-white uppercase tracking-wider">
              Dual-Channel Conversation Transcript
            </h3>
            <span className="text-[11px] font-mono text-[#94a3b8]">{turns.length} turns</span>
          </div>

          <div ref={transcriptRef} className="flex-1 p-6 space-y-4 overflow-y-auto">
            {turns.length === 0 && (
              <div className="flex flex-col items-center justify-center py-24 text-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-[#181826] border border-[#28283c] flex items-center justify-center text-[#64748b]">
                  <Volume2 size={20} />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-headline font-bold text-white">No active utterances yet</p>
                  <p className="text-xs text-[#94a3b8] max-w-sm">
                    Press the green Phone button to activate your browser mic, or click one of the quick test prompt chips on the left.
                  </p>
                </div>
              </div>
            )}

            {turns.map((t, i) => (
              <div key={i} className={`flex ${t.role === "agent" ? "justify-start" : "justify-end"}`}>
                <div
                  className={`max-w-[82%] rounded-2xl px-4 py-3 text-xs sm:text-sm leading-relaxed shadow-sm ${
                    t.role === "agent"
                      ? "bg-[#181828] text-[#f1f5f9] border border-[#2c2c40]"
                      : "bg-[#ff2d78]/15 text-white border border-[#ff2d78]/40"
                  }`}
                >
                  <div className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#94a3b8] mb-1">
                    {t.role === "agent" ? (activeTenant.agent_name || "Vaani (AI Agent)") : "Caller"}
                  </div>
                  {t.text}
                </div>
              </div>
            ))}
          </div>

          {actions.length > 0 && (
            <div className="border-t border-[#28283c] p-4 bg-[#10101a] max-h-48 overflow-y-auto space-y-2">
              <div className="text-[11px] font-mono uppercase tracking-wider text-[#00ffcc] font-bold flex items-center gap-2">
                <Volume2 size={13} />
                <span>Backend Function Calls Executed</span>
              </div>
              <div className="space-y-1.5">
                {actions.map((a, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs font-mono bg-[#141422] p-2 rounded-lg border border-[#242436]">
                    <span className="px-2 py-0.5 rounded bg-[#ff2d78]/15 text-[#ff2d78] font-bold">{a.name}</span>
                    <span className="text-[#94a3b8] truncate">{JSON.stringify(a.args)}</span>
                    {a.result && (
                      <span className="text-[#00ffcc] truncate">→ {JSON.stringify(a.result)}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------- helpers ----------

function bytesToBase64(bytes: Uint8Array): string {
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode.apply(null, Array.from(bytes.subarray(i, i + chunk)));
  }
  return btoa(binary);
}

function base64ToBytes(b64: string): Uint8Array {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}
