# VoxFlow — Build Plan Overview

This folder contains the day-by-day build plan. Work through phases in
order. Do not skip ahead to voice integration (Phase 3) before the text-only
core (Phase 2) is fully working — debugging conversation logic is much
faster in text than in voice, and voice bugs on top of untested logic bugs
will waste days.

Each day file has three sections:

- **Theory** — the concept you need to understand before doing the task,
  so you're not copy-pasting blind
- **Checklist** — concrete tasks for the day
- **Definition of Done** — how you know you're actually finished, not just
  "worked on it"

Mark items done directly in these files (`- [x]`) as you go. If a day's
tasks don't fit in a day, that's fine — the point of the checklist is
sequencing, not a deadline.

## Phases

| Phase | File | Focus | Est. days |
|---|---|---|---|
| 0 | phase-0-setup.md | Repo, env, accounts, schema draft | 1–2 |
| 1 | phase-1-foundation.md | DB schema in Supabase, seed data | 2 |
| 2 | phase-2-core-agent.md | Text-only conversation agent (LangGraph) | 4 |
| 3 | phase-3-voice-integration.md | Twilio + STT + TTS wired to the agent | 4 |
| 4 | phase-4-multitenancy-auth.md | Tenant isolation, staff auth, caller auth | 4 |
| 5 | phase-5-dashboard-realtime.md | Live dashboard, call logs, escalation UI | 3 |
| 6 | phase-6-pilot-launch.md | Real conversation with friend, pilot with one tenant, fixes | ongoing |

## Hard rule for this project

Do not write Phase 4 (multi-tenancy) content as final until you've had the
real conversation with your friend about Warren/Varun Beverages' actual
workflow (see PRD.md section 0 and 13). Phase 6 explicitly starts with that
conversation — everything before it can be built on reasonable assumptions,
but don't let assumptions harden into "done."
