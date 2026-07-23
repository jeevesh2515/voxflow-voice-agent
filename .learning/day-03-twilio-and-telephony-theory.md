# Day 3 — Twilio And Telephony Theory

## Status

Complete. Theory studied, ready for Week 2 implementation after Week 1 async DB fix.

## Main learning goal

Understand how Twilio Voice and Media Streams work, how audio flows through a real phone call, and what changes are needed to bridge the current browser-only voice pipeline to real telephony.

The important senior AI engineering lesson:

> Browser audio and phone audio are fundamentally different formats. Transcoding is not an edge case — it's the core integration challenge when moving from a simulator to real telephony.

## What I learned

### 1. Twilio Voice flow

```
Phone call → Twilio number → HTTP webhook to FastAPI → TwiML response
                           → Media Streams WebSocket (bidirectional audio)
```

**Inbound call webhook:** When someone calls the Twilio number, Twilio sends an HTTP POST to a configured webhook URL. The server responds with TwiML (Twilio Markup Language) — XML instructions telling Twilio what to do.

**TwiML for Media Streams:**
```xml
<Response>
  <Connect>
    <Stream url="wss://my-server.com/twilio/audio">
      <Parameter name="tenant_id" value="..." />
    </Stream>
  </Connect>
</Response>
```

This opens a WebSocket where Twilio sends audio frames from the caller and expects audio frames to play back.

### 2. Audio format differences

| Aspect | Browser simulator | Twilio phone call |
|---|---|---|
| Sample rate | 16kHz | 8kHz |
| Encoding | PCM (raw) | mulaw (μ-law) |
| Format | Float32 | Base64-encoded mulaw |
| Channels | Mono | Mono |

**Key format conversions needed:**

```
Twilio WebSocket → base64 decode → mulaw→PCM → 8kHz→16kHz → STT (faster-whisper)
TTS output → 16kHz PCM → 8kHz→mulaw → base64 encode → Twilio WebSocket
```

The Python `audioop` module handles mulaw↔PCM conversion. Sample rate conversion (8kHz↔16kHz) can use `audioop.ratecv()` or the `av` library which is already a dependency.

### 3. Twilio Media Streams protocol

Each WebSocket message from Twilio is JSON:

```json
{
  "event": "media",
  "streamSid": "MZ...",
  "media": {
    "payload": "base64-encoded-mulaw-audio"
  }
}
```

Event types:
- `connected` — WebSocket established
- `start` — stream is starting, includes `streamSid` and call metadata
- `media` — audio payload (every ~20ms during speech)
- `stop` — call ended

The server sends audio back as similar JSON:
```json
{
  "event": "media",
  "streamSid": "MZ...",
  "media": {
    "payload": "base64-encoded-mulaw-audio"
  }
}
```

### 4. End-of-utterance detection for phone audio

The current browser simulator may use a different silence threshold than what works for phone audio. Phone calls have:
- More background noise
- Lower audio quality (8kHz, compressed)
- Potentially louder breathing/line noise

The silence threshold and hold time may need tuning. A fixed threshold is fine for v1 — adaptive VAD can come later if needed.

### 5. Mapping phone number to tenant

Each Twilio phone number maps to one tenant. This means:
- New table: `tenant_phone_numbers(tenant_id, phone_number)` — one-to-many
- A distributor may have multiple numbers (one per region)
- On inbound call, look up the `to` number against this table to resolve `tenant_id`

This is simpler than asking the caller "which company are you calling?" via voice.

### 6. Architecture changes for Twilio

The existing `voice/pipeline.py` handles browser WebSocket audio. Twilio needs a parallel path:

```
Browser WebSocket → existing ws.py route → VoicePipeline
Twilio WebSocket  → new /twilio/audio route → VoicePipeline (reused)
```

The `VoicePipeline` itself should be reusable — only the audio input/output adapters change. The STT→agent→TTS core stays identical.

### 7. Deployment considerations

- The Twilio webhook must be reachable on a public HTTPS URL
- WebSocket connections from Twilio need a publicly accessible wss:// endpoint
- For local development: ngrok exposes localhost with HTTPS
- For production: Railway/Render/Fly.io with proper domain + SSL

### 8. Testing approach

1. **Static TwiML test** — webhook returns a TwiML that plays an audio file
2. **Echo test** — WebSocket echoes audio back (caller hears themselves)
3. **Full loop** — STT → agent → TTS wired end-to-end

## What was studied

| Topic | Source |
| --- | --- |
| Twilio Voice webhooks | Twilio docs — Voice TwiML, \<Connect\>\<Stream\> |
| Media Streams protocol | Twilio Media Streams guide — WebSocket audio frames |
| mulaw audio encoding | ITU-T G.711 standard, Python `audioop` module |
| audioop for mulaw↔PCM | Python stdlib docs — `audioop.ulaw2lin()`, `audioop.lin2ulaw()` |
| Sample rate conversion | `audioop.ratecv()` — 8kHz↔16kHz |
| ngrok for dev | ngrok docs — HTTPS tunnels for localhost |
| Twilio phone number→tenant mapping | Twilio inbound call `To` parameter |

## Key insight

The hardest part of adding telephony isn't the Twilio API — it's the audio format conversion. The browser simulator uses 16kHz PCM, but Twilio sends 8kHz mulaw. Every audio frame needs a base64→mulaw→PCM→resample pipeline on the way in, and the reverse on the way out. Getting this wrong means the STT model hears gibberish or the caller hears noise.

## Interview explanation

I studied Twilio's voice integration to prepare for adding real phone capability to VoxFlow. The key challenge is audio transcoding: Twilio sends 8kHz mulaw-encoded audio over WebSockets, but our local STT expects 16kHz PCM. I mapped out the conversion pipeline using Python's `audioop` module and identified the architecture changes needed — a new `/twilio/audio` WebSocket route that reuses the existing VoicePipeline with adapted audio I/O.

## Non-technical explanation

Right now, the voice agent works in a browser simulator — you click a button and talk into your computer. To make it work on a real phone call, we need to connect it to Twilio (a phone service). The main challenge is that phone audio and computer audio use different formats, so every sound needs to be converted between the two. I've studied exactly what conversions are needed and how to wire it up.

## Day 3 outcome

Thorough understanding of the Twilio integration path, audio transcoding requirements, and architecture changes needed for real telephony.

## Next step after Day 3

Day 4 — implement the async DB migration (Week 1 Day 1 of PHASES.md). The theory is ready; now it's time to execute.
