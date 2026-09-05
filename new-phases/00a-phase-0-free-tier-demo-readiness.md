# Phase 0: Free-Tier Demo Readiness (Pre-Funding)

## Objective

Get the current stack — Oracle Cloud Always-Free VM, Supabase free tier, and
the existing AWS Connect/Lex/Lambda telephony bridge — into a state reliable
and complete enough to demo confidently to a design partner or investor.
Total new spend cap: **$50 one-time/setup costs**, not counting the AWS
telephony usage you're already carrying (~$10/mo for DIDs and Connect/Lex
usage) and not counting AI/coding-agent costs, which are budgeted separately.

This phase does NOT lack features relative to the funded plan — it uses free
or genuinely-free-tier equivalents of everything, and Phase 1 (funded
migration) upgrades the underlying infrastructure later without changing what
the product does.

## Prerequisites

None. This is the phase you run right now, before any funding or revenue.

## Assumption stated up front

Treating the $50 cap as covering one-time/setup costs (primarily a domain
name, ~$10-15/year) and small recurring tool costs if genuinely unavoidable
— not as including the AWS telephony usage you already described as an
accepted ongoing cost. If that's wrong, tell me and the numbers below need
rechecking.

## Tools required (all free tier, verified)

- **Supabase** (free tier: 500 MB Postgres storage, 50K MAU, 5 GB egress +
  5 GB CDN cached egress, up to 2 active projects) — replaces SQLite as the
  database. Real Postgres, not a toy — this is why Phase 2 (Stripe) doesn't
  have to wait for the funded AWS migration.
- **Oracle Cloud Always-Free ARM VM** (already in use) — continues hosting
  FastAPI + Next.js via Docker Compose + Caddy (Caddy gives free automatic
  HTTPS via Let's Encrypt).
- **Alembic** — same as the funded plan, just targeting Supabase instead of
  RDS for now.
- **Sentry** (free Developer tier — enough error visibility for pre-launch)
- **Resend** (free tier: 100 emails/day, 3,000/month — plenty at this stage)
- **Crisp** (free tier, 2 seats) instead of HelpScout
- **PostHog** (free tier: 1M events/month) instead of Plausible, which has
  no free tier
- A domain name (~$10-15/year — the one real cost in this phase)

## Working steps

1. **Harden the Oracle VM for reliability, not just uptime.** Confirm Docker
   Compose services have a restart policy (`restart: unless-stopped`) so a
   VM reboot doesn't require manual intervention before a demo. Confirm
   Caddy's HTTPS cert renewal is actually working, not just configured.
2. **Migrate off SQLite onto Supabase.** Point `DATABASE_URL` at the Supabase
   project. Run Alembic's initial migration against it and verify schema
   parity against the current SQLite database, same verification standard as
   the funded plan.
3. **Fix the auto-pause risk.** Supabase free projects pause after a week of
   inactivity. Set up a lightweight scheduled ping (a cron job or GitHub
   Action hitting a health-check endpoint every 2-3 days) so the project
   never goes quiet long enough to pause. Don't rely on remembering to check
   before a demo — automate it.
4. **Secrets: `.env` on the VM, not a paid secrets manager.** Restrict file
   permissions (`chmod 600`), confirm `.env` is git-ignored, and check git
   history for any previously committed real secrets — rotate anything found.
   This is a lower-security stopgap appropriate for pre-revenue, pre-real-
   customer-data scale; Phase 1 upgrades this to AWS Secrets Manager once
   funded.
5. **Superadmin scaffold.** Same as the funded plan: `IS_SUPERADMIN` on
   `tenant_members`, a hidden `/superadmin` route listing tenants and minutes
   used. This is free — just code — and gives you visibility from day one.
6. **Backups: scripted, not automatic.** Supabase's free tier has no
   point-in-time recovery. Write a scheduled `pg_dump` script (cron on the
   Oracle VM) pushing to a free off-VM location — a private GitHub repo or a
   free-tier object store. Actually run one restore test before calling this
   done.
7. **Wire in Sentry, Resend, Crisp, PostHog.** Same integration work as the
   funded plan describes, just on free tiers. Verify each with a real test
   event, not a "should work."
8. **Status visibility: DIY, not a paid tool.** A simple static status page
   (hosted free on GitHub Pages or Vercel) updated by the same health-check
   script from step 3 is enough for this stage — don't pay for Better Stack
   yet.
9. **Legal stopgap, explicitly flagged as temporary.** Use a free ToS/Privacy
   Policy generator (e.g., Termly's free tier) to get baseline documents live.
   **This is not a substitute for a solicitor review** — it's acceptable for
   demo/trial framing with non-binding terms, but do not use it to take real
   payment or sign a real contract. Phase 3 (legal upgrade) replaces this
   with a solicitor-reviewed version.
10. **Call-recording disclosure — do this now, it's free.** Add the spoken
    (or DTMF) recorded-line disclosure to the Connect call flow. This is a
    code change, costs nothing, and protects you even during demo calls with
    real phone numbers. Don't wait for funding to do this one.
11. **Buy the domain.** This is the one real spend in this phase.

## Definition of Done

- [ ] Oracle VM services restart automatically on failure/reboot; HTTPS
      renewal confirmed working
- [ ] App runs against Supabase Postgres; SQLite fully retired
- [ ] Automated keep-alive ping confirmed preventing project auto-pause over
      at least one full week, tested, not assumed
- [ ] No real secrets in the repo or git history; anything found has been
      rotated
- [ ] `/superadmin` live and correctly listing tenants
- [ ] Backup script running on schedule; one manual restore tested and
      verified
- [ ] Sentry, Resend, Crisp, and PostHog all verified with a real test event
      each
- [ ] DIY status page live and reflecting real health-check state
- [ ] ToS/Privacy Policy published, clearly labeled as template-based
      pending solicitor review
- [ ] Call-recording disclosure verified on an actual test call
- [ ] Domain purchased and pointed at the Oracle VM
- [ ] Total new spend at or under $50, domain included
- [ ] Full existing test/eval suite still passes at 100%

## Explicitly out of scope for this phase

- AWS RDS, ECS Fargate, AWS Secrets Manager — Phase 1, funded only
- Drata/Vanta, SOC 2 evidence collection — funded only, real money involved
- HelpScout, Better Stack paid tier, solicitor-reviewed legal — upgrades that
  happen once revenue or funding justifies them
