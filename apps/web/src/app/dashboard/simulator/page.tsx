"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Mic, MicOff, Phone, PhoneOff, Send, Volume2, Loader2 } from "lucide-react";
import Topbar from "@/components/Topbar";

type Turn = { role: "caller" | "agent"; text: string; at: number };

const WS_URL = (typeof window !== "undefined" && process.env.NEXT_PUBLIC_WS_URL) || "ws://localhost:8000";

export default function PhoneSimulator() {
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
    const ws = new WebSocket(`${WS_URL}/ws/call`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      ws.send(JSON.stringify({ type: "start", language }));
      setTurns([
        { role: "agent", text: "नमस्ते, VoxFlow में आपका स्वागत है। मैं वाणी हूँ।", at: Date.now() },
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
            const blob = new Blob([bytes], { type: msg.agent_audio_mime || "audio/mpeg" });
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
  }, [language]);

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

  // ---------- Render ----------

  return (
    <>
      <Topbar title="Phone simulator" subtitle="Browser mic → Vaani · live" />
      <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-[400px_1fr]">
        {/* Left: phone */}
        <div className="border-r border-ink-700/60 p-6 flex flex-col">
          <div className="rounded-2xl bg-gradient-to-br from-ink-900 via-ink-800 to-ink-900 border border-ink-700/60 p-6 shadow-glow">
            <div className="text-center mb-6">
              <div className="inline-flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-ink-400 mb-1">
                <span className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-success-500 pulse-dot" : "bg-ink-500"}`} />
                {connected ? "live" : "offline"}
              </div>
              <div className="text-lg font-semibold text-ink-50">Vaani</div>
              <div className="text-[11px] font-mono text-ink-400">VoxFlow Voice Agent</div>
            </div>

            <div className="grid grid-cols-3 gap-2 mb-4">
              <button
                onClick={() => setLanguage("hi")}
                className={`py-2 rounded-md text-xs font-mono uppercase tracking-wider border ${
                  language === "hi" ? "bg-vox-500/15 border-vox-500/40 text-vox-300" : "border-ink-700/60 text-ink-300 hover:border-ink-600"
                }`}
              >
                हिन्दी
              </button>
              <button
                onClick={() => setLanguage("en")}
                className={`py-2 rounded-md text-xs font-mono uppercase tracking-wider border ${
                  language === "en" ? "bg-vox-500/15 border-vox-500/40 text-vox-300" : "border-ink-700/60 text-ink-300 hover:border-ink-600"
                }`}
              >
                EN
              </button>
              <button
                onClick={manualCommit}
                className="py-2 rounded-md text-xs font-mono uppercase tracking-wider border border-ink-700/60 text-ink-300 hover:border-ink-600"
                title="Send buffered audio to STT now"
              >
                Commit
              </button>
            </div>

            <div className="flex items-center justify-center gap-3 mb-4">
              {!connected ? (
                <button
                  onClick={() => { connect(); }}
                  className="h-14 w-14 rounded-full bg-success-500 hover:bg-success-500/90 grid place-items-center text-white shadow-glow"
                  aria-label="Start call"
                >
                  <Phone size={22} />
                </button>
              ) : (
                <button
                  onClick={disconnect}
                  className="h-14 w-14 rounded-full bg-danger-500 hover:bg-danger-500/90 grid place-items-center text-white"
                  aria-label="End call"
                >
                  <PhoneOff size={22} />
                </button>
              )}
              <button
                onClick={recording ? stopMic : startMic}
                disabled={!connected}
                className={`h-14 w-14 rounded-full grid place-items-center border ${
                  recording
                    ? "bg-danger-500/20 border-danger-500/50 text-danger-500"
                    : "bg-ink-800 border-ink-700 text-ink-300 hover:bg-ink-700"
                } disabled:opacity-40`}
                aria-label={recording ? "Stop mic" : "Start mic"}
              >
                {recording ? <MicOff size={20} /> : <Mic size={20} />}
              </button>
            </div>

            {recording && (
              <div className="flex items-center justify-center mb-4">
                <span className="audio-bar" />
                <span className="audio-bar" />
                <span className="audio-bar" />
                <span className="audio-bar" />
                <span className="audio-bar" />
              </div>
            )}

            <div className="text-center text-[11px] font-mono text-ink-500">
              {callId ? `call ${callId.slice(0, 18)}…` : "no call"}
            </div>
          </div>

          {/* Text fallback */}
          <div className="mt-4">
            <label className="text-[11px] font-mono uppercase tracking-wider text-ink-400 mb-1.5 block">
              Or type a message
            </label>
            <div className="flex gap-2">
              <input
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && sendText()}
                placeholder="e.g. मुझे 50 case Pepsi 250ml चाहिए"
                className="flex-1 bg-ink-900 border border-ink-700/60 rounded-md px-3 py-2 text-sm text-ink-100 placeholder:text-ink-500 focus:outline-none focus:border-vox-500"
              />
              <button
                onClick={sendText}
                disabled={busy || !textInput.trim()}
                className="px-3 rounded-md bg-vox-500 hover:bg-vox-600 disabled:opacity-40 text-white"
                aria-label="Send"
              >
                {busy ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
              </button>
            </div>
          </div>

          {error && (
            <div className="mt-3 text-xs text-danger-500 border border-danger-500/30 bg-danger-500/10 rounded-md p-2">
              {error}
            </div>
          )}

          <div className="mt-auto pt-4 text-[10px] font-mono text-ink-500 leading-relaxed">
            <div>WS: {WS_URL}/ws/call</div>
            <div>Tip: speak a 1-second phrase, then pause. Auto-commits on silence.</div>
          </div>
        </div>

        {/* Right: transcript + actions */}
        <div className="flex flex-col min-h-0">
          <div ref={transcriptRef} className="flex-1 min-h-0 overflow-y-auto p-6 space-y-3">
            {turns.length === 0 && (
              <div className="text-center text-sm text-ink-500 py-12">
                Start the call to begin. Or type a message to test the agent without audio.
              </div>
            )}
            {turns.map((t, i) => (
              <div key={i} className={`flex ${t.role === "agent" ? "justify-start" : "justify-end"}`}>
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                    t.role === "agent"
                      ? "bg-ink-800 text-ink-100 border border-ink-700/60"
                      : "bg-vox-500/15 text-ink-50 border border-vox-500/30"
                  }`}
                >
                  <div className="text-[10px] font-mono uppercase tracking-wider text-ink-500 mb-0.5">
                    {t.role === "agent" ? "Vaani" : "Caller"}
                  </div>
                  {t.text}
                </div>
              </div>
            ))}
          </div>

          {actions.length > 0 && (
            <div className="border-t border-ink-700/60 px-6 py-3 bg-ink-900/40 max-h-48 overflow-y-auto">
              <div className="text-[11px] font-mono uppercase tracking-wider text-ink-400 mb-2 flex items-center gap-2">
                <Volume2 size={12} /> Actions taken
              </div>
              <div className="space-y-1.5">
                {actions.map((a, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <span className="px-1.5 py-0.5 rounded bg-vox-500/15 text-vox-300 font-mono">{a.name}</span>
                    <span className="font-mono text-ink-400 truncate">
                      {JSON.stringify(a.args)}
                    </span>
                    {a.result && (
                      <span className="text-ink-500 truncate">→ {JSON.stringify(a.result).slice(0, 80)}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </>
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
