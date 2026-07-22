# VoxFlow — Build Plan Overview

This folder contains the day-by-day build plan. Work through phases in order.

## Phases Status

| Phase | File | Focus | Status |
|---|---|---|---|
| 0 | phase-0-setup-planning-file.md | Repo, env, accounts, schema draft | ✅ Completed |
| 1 | phase-1-database-foundation.md | DB schema in Supabase, seed data | ✅ Completed |
| 2 | phase-2-auth-multi-tenant-dashboard.md | Auth flow, multi-tenant workspace & company dashboard | ✅ Completed (Day 2) |
| 3 | phase-3-voice-integration-planning-file.md | Twilio + STT + TTS wired to voice agent | 🚀 Up Next (Day 3) |
| 4 | phase-4-multi-tenancy-and-auth-planning.md | Advanced caller auth, PIN verification, RLS policies | Planned |
| 5 | phase-5-dashboard-and-realtime-planning.md | Realtime voice stream & escalation UI | Planned |
| 6 | pilot-launch | Real conversation & pilot onboarding | Planned |

---

## Hard Rule for VoxFlow

Tenant isolation (`tenant_id`) is strictly enforced at every level — DB queries, state stores, and UI dashboards scope company data strictly to the active workspace.
