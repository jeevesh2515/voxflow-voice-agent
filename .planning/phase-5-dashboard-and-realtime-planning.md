# Phase 5 — Dashboard & Real-Time Updates (Day 17–19)

You said the frontend + brand kit already exist — this phase is about
wiring your existing Next.js frontend to real data, not designing a new UI
from scratch.

## Day 17

### Theory

Supabase Realtime lets your frontend subscribe to Postgres changes (new
rows in `call_logs`, updates to an in-progress call) without polling.
This is what makes the "real-time updates during the call" requirement
actually real-time instead of a refresh button.

### Checklist

- [ ] Connect the existing Next.js frontend to Supabase (client + auth)
- [ ] Wire a live call_logs table view using Supabase Realtime
      subscriptions
- [ ] Confirm a new row appearing in `call_logs` (from a test call)
      appears in the dashboard without a manual refresh

### Definition of Done

Making a test call causes its log entry to appear on the dashboard live,
within a couple of seconds, no refresh needed.

## Day 18

### Theory

"What they are asking and what things have been done" during an active
call implies streaming partial state, not just the final log. This
requires either streaming transcript chunks to a `call_status` table as
the call progresses, or a lightweight pub/sub channel per active call.

### Checklist

- [ ] Add an in-progress call state update (e.g. a `call_status` table or
      row updated as the call progresses: current intent, entities
      captured so far)
- [ ] Wire the dashboard to show active calls with their live status
- [ ] Test: while a test call is in progress, the dashboard shows it
      updating in near real time

### Definition of Done

An active test call is visible on the dashboard while still in progress,
showing at least current intent and captured entities, updating live.

## Day 19

### Theory

Escalated calls (low confidence / auth failure / anything the agent
couldn't resolve) need to be visibly actionable for staff, not buried in
a log. This is the safety net that makes the whole system trustworthy to
a real business owner.

### Checklist

- [ ] Add an "escalated calls" view/filter on the dashboard, distinct
      from completed calls
- [ ] Add a manual note/resolution field staff can fill in once they've
      followed up on an escalated call
- [ ] Test: an escalated test call appears clearly flagged and can be
      marked resolved

### Definition of Done

An escalated call is visually distinct on the dashboard and can be marked
resolved by a staff user, with that resolution persisted.
