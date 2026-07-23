# Daily Learning Journal — VoxFlow Voice Agent

This folder is the private daily learning and implementation journal for the VoxFlow project — a bilingual (Hindi/English) voice AI agent for FMCG distributors in India.

## Privacy rule

This folder is intentionally private/local. It should **not** be pushed to GitHub. Add `.learning/` to `.gitignore` if not already present.

## Agent update rule

Whenever any future agent or coding session changes the project, update this folder if the change affects learning progress, implementation status, validation status, next steps, or architecture understanding.

Minimum update expectations:

1. Update the current day file when work is done for that day.
2. Add a new `day-NN-*.md` file when starting a new learning day.
3. Record: what was learned, what was implemented, what files changed, what validation was run, what errors or surprises came up, what the next day should focus on.
4. Keep this journal practical and interview-useful.
5. Do not include secrets, credentials, private tokens, or real API keys.

## Current files

- `day-01-project-foundation-and-vision.md`
- `day-02-async-db-and-latency-theory.md`
- `day-03-twilio-and-telephony-theory.md`
- `day-04-next-up-async-db-implementation.md`

## Current learning status

| Day | Topic | Status |
| --- | --- | --- |
| Day 1 | Project Foundation And Vision | ✅ Complete |
| Day 2 | Async DB And Latency Theory | ✅ Complete |
| Day 3 | Twilio And Telephony Theory | ✅ Complete |
| Day 4 | Async DB Implementation (Week 1 Day 1) | 📋 Planned |

## Current completed phases

- **Phase 0** — Repo setup, FastAPI skeleton, Supabase/Groq/Twilio config, Next.js frontend scaffold
- **Phase 1** — Database schema with multi-tenant models, RLS policies, seed data across 4 tenants
- **Phase 2** — Staff sign-up/sign-in flows, multi-tenant dashboard with workspace switcher, session persistence

## Current phase in progress

- **Phase 3 — Voice Integration (Twilio)** — async DB layer must be fixed first (Week 1)

## Next up

See [day-04-next-up-async-db-implementation.md](./day-04-next-up-async-db-implementation.md) for the next implementation checklist: convert synchronous SQLAlchemy to async, add caching layer, fix Supabase connection hygiene.
