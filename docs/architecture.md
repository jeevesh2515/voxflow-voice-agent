# Architecture

## High-level

```
Browser phone simulator
   │  WebSocket: {type:"pcm", data:"<b64 int16 16kHz>"}   in
   │  WebSocket: {type:"turn", agent_text, agent_audio_b64}  out
   ▼
FastAPI server (apps/api)
   │
   ├── STT: faster-whisper (local, CPU)
   │     │  PCM @ 16kHz mono int16
   │     │  → text + detected language
   │     ▼
   ├── Agent runner
   │     │
   │     ├── System prompt (Hindi+English aware)
   │     ├── Tool dispatcher
   │     │     ├── lookup_supplier
   │     │     ├── check_stock
   │     │     ├── get_shipment_status
   │     │     ├── create_po
   │     │     ├── verify_po
   │     │     └── escalate_to_human
   │     ├── LLM (pluggable: Ollama | Groq | OpenRouter)
   │     └── Conversation history (per CallSession)
   │
   ├── TTS: edge-tts (Microsoft) — picks Hindi or English voice by detected script
   │
   └── SQLite (dev) / Postgres (prod)
         ├── suppliers
         ├── products
         ├── stock
         ├── orders
         ├── shipments
         └── calls   (transcript + actions + outcome)

Next.js dashboard (apps/web)
   ├── /             landing
   ├── /dashboard    overview (SWR polling)
   ├── /dashboard/simulator   mic + WebSocket + transcript
   ├── /dashboard/calls       call log + transcripts
   ├── /dashboard/orders      order list
   ├── /dashboard/shipments   shipment timeline
   ├── /dashboard/stock       stock by warehouse
   └── /dashboard/suppliers   supplier directory
```

## LLM provider swap

The factory in `apps/api/voxflow_api/llm/factory.py` returns a single
`LLMProvider` instance. Switching providers is a one-line env change:

```env
LLM_PROVIDER=ollama        # or groq | openrouter
```

All three implement the same async `chat(messages, tools)` interface, so the
agent runner is provider-agnostic. Tool-call JSON is normalised to the OpenAI
format that all three accept.

## Voice pipeline

1. Browser captures mic → `AudioContext` at 16kHz mono.
2. `ScriptProcessor` produces 4096-sample buffers, converted to int16 PCM.
3. Each buffer is base64-encoded and sent as a `pcm` message over WebSocket.
4. The server buffers PCM, runs `faster-whisper` on `commit` (manual or auto on silence).
5. STT result goes into `CallSession.transcript` and into the agent's history.
6. Agent loop: LLM → tool calls (if any) → LLM → final reply.
7. Reply goes to `edge-tts` with the detected language; MP3 is streamed back.
8. Browser plays the MP3 and shows the transcript in the simulator UI.

## Database

SQLite for dev (`./voxflow.db`), Postgres for prod. Swap is a `DATABASE_URL`
env var. Schema is declared in `apps/api/voxflow_api/db.py` and created on
startup via `Base.metadata.create_all`. No migrations for MVP — re-seed with
`python -m voxflow_api.seed --reset` to start clean.

## Why these choices

| Decision | Why |
|---|---|
| Python 3.12 | Best AI/ML ecosystem, mature async, FastAPI |
| FastAPI | Async, type-safe, auto OpenAPI docs |
| faster-whisper | Free, local, accurate, CPU-runnable |
| Ollama / Groq / OpenRouter | Three free tiers, no vendor lock |
| edge-tts | Microsoft TTS — natural Hindi voices, no key |
| SQLite → Postgres | Zero config to start, painless upgrade |
| Next.js 14 App Router | Matches the MadeThis storefront stack |
| WebSocket | Streaming latency <500ms perceived |
