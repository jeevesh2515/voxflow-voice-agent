# Day 7 — Twilio Media Streams WebSocket (Week 2, Day 7)

## Status

**Completed.** Twilio Media Streams receive path wired. Audio frames flow from Twilio → server → decoded PCM.

## What was done

### Twilio routes (`routes/twilio.py` — new file)

- **`POST /twilio/voice`** — TwiML webhook endpoint. Returns XML that plays a Hindi greeting (`नमस्ते, वॉक्सफ़्लो में आपका स्वागत है।`) and opens a `<Connect><Stream>` WebSocket to `/twilio/media`. Hostname validated via regex to prevent SSRF.
- **`WebSocket /twilio/media`** — receives JSON messages from Twilio Media Streams:
  - `connected` event — logged
  - `start` event — captures `streamSid` and `callSid`
  - `media` event — base64-decodes mulaw payload, decodes to PCM, resamples
  - `stop` event — logs frame summary, breaks loop
  - `mark` event — silently handled (acknowledgement)
  - Unknown events — logged at debug level
- **`mulaw_to_pcm()`** — decodes 8-bit μ-law bytes to 16-bit signed linear PCM (little-endian) using a hand-rolled `_ulaw2linear()` expansion function. ~100 bytes, avoids deprecated `audioop` module.
- **`resample_8k_to_16k()`** — linear interpolation resampler. Doubles sample count. Good enough for Day 7; swap for `librosa.resample()` in production.
- **Frame logging** every 100th frame with `streamSid`, `frame_count`, `total_bytes`, `mulaw_len`, `pcm_16k_len`.

### Frontend double-Topbar fix

**Bug:** `DashboardLayout` rendered a global `<Topbar>` (brand, company selector, search, user menu), but every child page also rendered its own `<Topbar>` with page title. This created a double-Topbar layout on every dashboard page.

**Fix:** Replaced per-page `<Topbar>` imports with inline `<h1>` headers in all 8 dashboard pages:
- `calls/page.tsx` — "Call Logs & Transcripts"
- `orders/page.tsx` — "Purchase Orders"
- `shipments/page.tsx` — "Shipment Tracking"
- `stock/page.tsx` — "Stock & Inventory"
- `suppliers/page.tsx` — "Suppliers Directory"
- `appointments/page.tsx` — "Supplier Appointments"
- `communications/page.tsx` — "Outbound Communications Log"
- `simulator/page.tsx` — "Phone Simulator"

### PCM buffer safety (`pipeline.py`)

Added a 60s cap (~1.9 MB at 16kHz PCM) on `CallSession.pcm_buffer`. Prevents OOM on long calls where audio accumulates without flushing to STT.

### Requirements

Added `greenlet==3.5.4` — required by SQLAlchemy async engine (`AsyncSession`). Tests were failing with `the greenlet library is required to use this function`.

## Validation

- ✅ `pytest tests/test_api.py`: **15/15 passed**

## Files modified

| File | Change |
| --- | --- |
| `apps/api/voxflow_api/routes/twilio.py` | **New** — TwiML endpoint + Media Streams WebSocket handler |
| `apps/api/voxflow_api/main.py` | Register twilio router |
| `apps/api/voxflow_api/voice/pipeline.py` | PCM buffer cap at 1.92 MB (60s) |
| `apps/api/requirements.txt` | Added `greenlet` |
| `apps/web/src/app/dashboard/*/page.tsx` (8 files) | Replaced per-page Topbar with inline headers |
| `ARCHITECTURE.md` | Updated Twilio integration section with Day 7 status |
| `MEMORY.md` | Updated current position, added Twilio items |
| `PHASES.md` | Marked Day 6-7 code items complete, added theory for Days 8-10 |

## Key lessons

1. **Twilio Media Streams protocol:** JSON messages with `event` field. Audio payload is base64-encoded 8-bit μ-law at 8kHz, ~160 bytes per frame (~20ms). No headers, no framing — just decode and buffer.
2. **μ-law decoding is simple math:** `~byte`, extract sign/exponent/mantissa, compute `((mantissa << 3) + 0x84) << (exponent + 2)`, apply sign. No library needed.
3. **`greenlet` is a transitive dep:** SQLAlchemy async mode uses greenlets internally. Not listed in SQLAlchemy's own deps — must add explicitly. Tests fail with `ModuleNotFoundError: No module named 'greenlet'` if missing.
4. **Component hierarchy matters:** When a layout already renders a global component, child pages importing the same component create duplicates. Fix at the source: remove imports from children, not from layout.

## Still pending

- ❌ Twilio account not yet configured — needs real phone number to test end-to-end
- ❌ Day 8: Wire STT into Twilio stream (audio buffer → VAD → SpeechToText)
- ❌ Day 9-10: Full loop with TTS + multi-caller testing

## Next up

Day 8 — Wire STT into the Twilio stream. See `.learning/day-08-stt-into-twilio-stream.md`.
