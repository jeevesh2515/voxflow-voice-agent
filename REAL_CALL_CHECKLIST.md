# VoxFlow — Real Phone Call Checklist

**This is the single highest-priority item.** Every layer is unit-tested; nothing is proven until one live call completes.

Last updated: 2026-08-13

---

## Prerequisites (already mostly done)

- [x] Oracle VM + Caddy TLS at `https://voxflow-jeevesh.duckdns.org`
- [x] Supabase schema + RLS policies applied
- [x] Demo data seeded
- [x] `python -m voxflow_api.selftest` green on the box
- [x] Twilio account + trial number available
- [x] Codec path (mulaw ↔ PCM), VAD, STT, agent, TTS all coded

---

## Steps to first real call

### 1. Confirm public URL is healthy

```bash
curl -s https://voxflow-jeevesh.duckdns.org/docs | head
# or health endpoint if you have one
```

### 2. Point Twilio voice webhook

Twilio Console → Phone Numbers → your number → Voice & Fax:

| Setting | Value |
|---------|--------|
| A CALL COMES IN | Webhook |
| URL | `https://voxflow-jeevesh.duckdns.org/twilio/voice` |
| Method | `HTTP POST` |

Save.

### 3. Register the number against a tenant

In Supabase SQL editor (or via seed):

```sql
INSERT INTO tenant_phone_numbers (tenant_id, phone_e164, label)
VALUES ('varun', '+44XXXXXXXXXX', 'UK trial')
ON CONFLICT DO NOTHING;
```

Use the exact E.164 number from Twilio (with `+`).

### 4. Env vars on the Oracle box

Confirm these are set in the production `.env` / compose:

```bash
PUBLIC_BASE_URL=https://voxflow-jeevesh.duckdns.org
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_VALIDATE_SIGNATURE=true   # keep on in prod
GROQ_API_KEY=...
DATABASE_URL=...                 # Supabase direct/session string
```

Redeploy / restart if you changed anything:

```bash
cd /path/to/voxflow && docker compose -f deploy/docker-compose.prod.yml up -d --build
```

### 5. Make the call

1. Call the Twilio number from your mobile.
2. You should hear the agent greeting (edge-tts).
3. Speak a simple line: *"I want to check the status of my order."*
4. Complete verification if prompted (company + city / GSTIN / contact name from seed data).
5. Hang up cleanly.

### 6. Verify success

On the server logs:

```bash
docker compose -f deploy/docker-compose.prod.yml logs -f api | grep -E 'twilio|transcript|agent'
```

In the dashboard (`/dashboard/calls`):
- New row appears after refresh (realtime is still P1)
- Transcript present
- `verified` / outcome fields populated if flow completed

In Postgres:

```sql
SELECT id, caller_phone, reason, resolution_status, verified, created_at
FROM calls
ORDER BY created_at DESC
LIMIT 5;
```

### 7. Capture latency & failure notes

Paste into `MEMORY.md` → Latency Baseline:
- STT time
- LLM turn time
- TTS start delay
- Total perceived turn time
- Any VAD issues (cut off early / late)

---

## Definition of Done

- [ ] At least **one full scenario** completed by voice (e.g. order status or stock check)
- [ ] Call row persisted even if caller hangs up mid-flow
- [ ] No dead air > ~2s attributable to Sheets / blocking I/O
- [ ] Numbers written into MEMORY.md

**Do not start Week 3 (Supabase Auth hardening / RLS verification / realtime) until this box is checked.** Auth work can be coded in parallel, but product priority is the live call.

---

## Common failures

| Symptom | Likely cause |
|---------|----------------|
| No answer / Twilio error | Webhook URL wrong, Caddy down, firewall |
| Silence after answer | TTS not streaming, or mulaw encode bug |
| Transcript empty | VAD too strict / too loose; STT key missing |
| Wrong tenant | `tenant_phone_numbers` not seeded for that number |
| 401 from Twilio | Signature validation — check `TWILIO_AUTH_TOKEN` |
| Call not in DB | Finalize path / `CancelledError` (should be fixed; re-check logs) |
