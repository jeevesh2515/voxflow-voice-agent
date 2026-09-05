# VoxFlow SaaS-Readiness Roadmap — Master Index

This roadmap has 9 phases across 3 files each: a free-tier bootstrap phase
you run now, a funded infrastructure migration, and 7 phases that build out
the rest of the product. It is not a strict 1-through-7 chain — several
phases can run in parallel, noted below.

## How to use this with a coding agent

- **One phase per session.** Don't paste multiple phase files into the same
  conversation and let the agent range across them.
- **Don't start a phase until its actual prerequisites (below) are met** —
  not just "the previous number," since several phases now depend on Phase 0
  alone, not on the funded migration.
- **If a step doesn't match reality** — a file, table, or function named in a
  phase doesn't actually exist in the repo — the agent should stop and report
  the discrepancy, not invent a plausible-sounding substitute and continue.
- **The existing test/eval suite (508 tests, 30 evals via
  `scripts/run_evals.py --strict`) must stay green after every phase.**

## Phase order and real dependencies

| Phase | Objective | Actually depends on |
|---|---|---|
| 0 | Free-Tier Demo Readiness (Oracle VM + Supabase, $50 cap) | Nothing — start now |
| 1 | Funded Infrastructure Migration (Supabase/Oracle → AWS-native) | Funding or revenue justifying the spend; Phase 0 done |
| 2 | Revenue Infrastructure (Stripe) | **Phase 0 only** — Supabase is real Postgres, don't wait for Phase 1 |
| 3 | Operational Trust (full build-out) | Phase 2 (billing events trigger emails); doesn't need Phase 1 |
| 4 | Legal & Compliance (solicitor review, DPA) | Phase 3; needed before real money changes hands regardless of funding |
| 5 | Go-to-Market Surface | Phases 0 and 3; claims must match current reality (free-tier or funded) |
| 6 | Enterprise Readiness (SSO, SOC 2, DR, load test) | Phase 1 (funded infra); SOC 2 evidence-collection specifically can start once Phase 1 lands |
| 7 | Scale & Retention | Phases 1-6, product already selling |

Phase 0 is the one to run right now. Phase 1 is gated on funding — everything
from Phase 2 onward can and should start on top of Phase 0 alone where the
table above says so, rather than waiting idle for Phase 1 to close.

## Corrections made, in order

1. **Postgres migration ahead of Stripe billing** (original issue): building
   financial records on SQLite then migrating was backwards. Resolved by
   Phase 0 using real Postgres (Supabase) from day one — see point 3.
2. **SOC 2 timeline decoupled from a fixed week number**: 8-12 weeks of work
   can't start at a fixed calendar point and still fit a 90-day claim. SOC 2
   evidence-collection now starts whenever its prerequisite controls are
   actually in place.
3. **Free-tier bootstrap phase added (Phase 0)**: no paying customers yet, no
   spend appetite before traction. Phase 0 delivers a demo-credible product
   on Supabase + Oracle Cloud free tier for under $50, with Phase 1 as a
   later migration once funded — not a rebuild.
4. **Revenue Infrastructure decoupled from the funded migration**: since
   Phase 0 uses real Postgres (Supabase, not SQLite), Stripe billing can be
   built immediately on top of it. Q1 pilots don't have to wait for AWS.

See `00a-phase-0-free-tier-demo-readiness.md` for the current phase to
execute, and `09-pitch-deck-crosscheck-findings.md` for the deck-specific
corrections (stale dates, Q1 billing story, ERP bridges, the now-resolved
Oracle Cloud question).
