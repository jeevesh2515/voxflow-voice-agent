# Phase 0 — Setup (Day 1–2)

## Day 1

### Theory

A SaaS that will eventually serve multiple companies needs its data model
to be tenant-aware from day one. Retrofitting `tenant_id` onto every table
later is painful and error-prone. It costs almost nothing to add it now,
even while you're the only "tenant."

### Checklist

- [x] Create GitHub repo `voxflow-voice-agent`
- [x] Set up Python virtual environment, FastAPI skeleton (`/health` route
      only, confirm it runs locally)
- [x] Create Supabase / Postgres database config, note project URL + anon key +
      service role key, store in `.env` (never commit `.env`)
- [x] Configure Twilio / Groq API settings in `.env`
- [x] Confirm STT/TTS provider configuration (faster-whisper / edge-tts / Deepgram / ElevenLabs)
- [x] Confirm existing Next.js frontend + brand kit in `/apps/web`

### Definition of Done

FastAPI app runs locally and returns 200 on `/health`. Database project
connects from local Python scripts. All API keys are in `.env`, `.env` is in `.gitignore`.

## Day 2

### Theory

Before writing any agent logic, you need to know exactly what data it will
read and write. Sketching the schema now — even a rough draft — prevents
building conversation logic around fields that don't exist yet.

### Checklist

- [x] Draft the schema on paper/markdown first (see PRD.md section 8):
      `tenants`, `suppliers`, `stock`, `orders`, `shipments`, `call_logs`,
      `users`, `appointments`, `worksheet_logs`, `communication_logs`
- [x] Write this draft into `schema.md` in the repo root
- [x] Create database schema models in `apps/api/voxflow_api/db.py`

### Definition of Done

`schema.md` exists with all table names, columns, and types drafted and implemented in the database model layer.
