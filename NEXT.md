# Day 8 — Wire STT into the Twilio stream

**Theory:** Day 7 delivers decoded 16kHz PCM frames inside the `/twilio/media`
WebSocket handler. Next step: feed those frames into the existing `SpeechToText`
pipeline (`voice/stt.py`) so real phone audio produces transcripts.

## Core problem

Twilio sends ~20ms audio frames. STT needs a complete utterance. Three things
must happen between receiving frames and running STT:

### 1. Audio buffering

Accumulate decoded/resampled PCM frames in a `bytearray` per call (keyed by
`callSid` from the Twilio `start` event). The buffer grows until an utterance
boundary is detected — then flush to STT.

### 2. Voice Activity Detection (VAD)

Two options:

- **Amplitude threshold** (simpler, Day 8 default) — measure RMS of each
  frame. Below threshold for ~700ms → end of utterance. Already works in
  `pipeline.py` `commit_audio()` path. Downside: noise not filtered.
- **`webrtcvad`** (better for phone audio) — purpose-built for telephony,
  handles noise gating. Add `webrtcvad==2.0.11` to `requirements.txt`.

### 3. Session wiring

On Twilio `start` event: create `CallSession` via `pipeline.start_session()`,
pass `callSid` as the call ID. On `stop` event: flush any remaining buffer,
call `pipeline.end_session()`.

## Implementation plan

1. In `routes/twilio.py`, add a dict mapping `streamSid` → buffer state:
   ```python
   _twilio_sessions: dict[str, dict[str, Any]] = {}
   ```
   Each entry holds: `call_sid`, `pcm_buffer: bytearray`, `last_audio_at: float`,
   `session: CallSession | None`.

2. On `start` event: create a buffer entry, optionally create a `CallSession`.

3. On `media` event: decode → resample → append to buffer. Update
   `last_audio_at`. Run VAD check.

4. On VAD silence: call `pipeline.commit_audio(session)` using the buffered
   PCM. This returns the agent's TTS audio — store it for streaming back
   (Day 9 handles the TTS→Twilio encoding).

5. On `stop` event: flush buffer, call `pipeline.end_session()`, clean up
   buffer entry.

## Checklist

- [ ] Feed decoded/resampled PCM into `SpeechToText` pipeline
- [ ] Implement end-of-utterance detection (amplitude VAD, ~700ms silence)
- [ ] Wire `callSid` → `CallSession` in Media Streams handler
- [ ] Log transcripts from real phone calls
- [ ] Verify with `webrtcvad` as upgrade path (optional Day 8)

## Definition of Done

Speaking a test sentence on a real Twilio call produces an accurate transcript
in the server logs (visible via the logger as `stt.result` or similar).

## Quick start for Day 8

```bash
# Run tests first
cd apps/api && uv run pytest -v

# Start the API server
uv run uvicorn voxflow_api.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, start the web dashboard
cd apps/web && npm run dev

# Configure a Twilio number to POST to:
#   http://YOUR_TUNNEL_URL/twilio/voice

# Use ngrok to expose localhost:
#   ngrok http 8000
```
