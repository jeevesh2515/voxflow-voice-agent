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
- `day-05-async-complete-and-caching.md`
- `day-06-frontend-polish-and-bugfix.md`

## Current learning status

| Day | Topic | Status |
| --- | --- | --- |
| Day 1 | Project Foundation And Vision | ✅ Complete |
| Day 2 | Async DB And Latency Theory | ✅ Complete |
| Day 3 | Twilio And Telephony Theory | ✅ Complete |
| Day 4 | Async DB Implementation | ✅ Complete |
| Day 5 | Cache Layer + Security Pass | ✅ Complete |
| Day 6 | Frontend Polish + Bug Fixes | ✅ Complete |

## Week 1 summary

All Week 1 objectives complete:

| Day | Actual work | Key outcome |
| --- | --- | --- |
| Day 1 | Async DB layer | All tools async, dual sync/async engines |
| Day 2 | TTL cache | `stock_cache` + `supplier_cache` on hot reads |
| Day 3 | Supabase hygiene | Documented direct/pooled switch, deferred to deploy |
| Day 4 | Timing & latency logs | `timing.stt`, `timing.tts`, `timing.tool`, `timing.persist` |
| Day 5 | Buffer/security | Live keys stripped, MEMORY.md updated, tests green |
| Day 6 | Frontend polish | Loading/error states, dead buttons fixed, `any`→types, mock data removed, cache bug fixed |

## What was fixed in the audit

- **Bug:** `lookup_supplier` cache.set after return statement (dead code since Day 2). Cache now properly populated.
- **Bug:** Cache hits skipped `session.supplier_id` assignment — fixed by restoring session state from cache data.
- **Bug:** `schedule_appointment` silently used `datetime.now()` on invalid input — now returns error.
- **Mock data removed:** Dashboard no longer shows fake call counts (12,482), fake orders (439), fake supplier images, or hardcoded interaction rows. All data now comes from API.
- **Fake stats stripped:** Topbar removed fake "12 Active Agents", "99.9% Uptime", "1,242 / 1,500 calls".
- **All 15 tests pass, 17/17 frontend pages compile.**

## Current completed phases

- **Phase 0** — Repo setup, FastAPI skeleton, Supabase/Groq/Twilio config, Next.js frontend scaffold
- **Phase 1** — Database schema with multi-tenant models, RLS policies, seed data across 4 tenants
- **Phase 2** — Staff sign-up/sign-in flows, multi-tenant dashboard with workspace switcher, session persistence
- **Week 1 polish** — Async DB, caching layer, timing instrumentation, frontend quality pass

## Next up

Week 2 — Twilio telephony integration and multi-tenancy hardening.
