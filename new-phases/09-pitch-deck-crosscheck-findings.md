# Pitch Deck Cross-Check Findings

Findings from comparing the investor deck against the 7-phase roadmap. Fix the
deck issues before showing it to anyone; the roadmap has already been updated
for the planning issues (see the "Updated" note under each item).

## 1. Stale roadmap dates — fix before showing this deck to anyone

`roadmap.html` labels Q1 as "Q4 2025 → Q1 2026" and frames it as "Where we
are." Today's date is well past that window. An investor will notice this in
seconds and it reads as neglect, not ambition. Relabel the quarters to your
actual current position, and be honest about which Q1 milestones (3 pilots,
SOC2 readiness, ERP bridges, $15K MRR) are actually done versus still pending.

## 2. Q1 pilots vs. Q2 Stripe billing — contradiction, needs a stated resolution

The roadmap slide claims $15K MRR / 3 paid pilots in Q1, but Stripe billing
is a Q2 line item. You cannot hit that MRR number with no billing system live
— unless the first 3 design partners are invoiced manually (bank transfer /
plain invoice) before Stripe automation exists. That's a completely normal
pattern for early pilots, but it isn't stated anywhere in the deck or the
original roadmap. State it explicitly on the slide or in speaker notes:
"first 3 pilots billed manually; Stripe automation ships in Q2 for scale."

**Updated:** Phase 2 (`02-phase-2-revenue-infrastructure.md`) now notes this
explicitly — manual invoicing for early pilots is fine and shouldn't block
Q1 revenue on Phase 2's completion, but those manual invoices need to be
reconciled into the real subscription/invoice tables once Phase 2 ships, not
left as an orphaned spreadsheet.

## 3. SOC 2 sequencing was too conservative

The deck wants SOC 2 Type I readiness in Q1. The original roadmap put it in
Phase 6, after billing, legal, and go-to-market — effectively months later.
That was overly cautious: the moat slide states the RBAC matrix, zero-leak
tenant isolation, and audit-trail logging already exist, which is exactly the
evidence Drata/Vanta need. There's no reason to wait for Phases 2-5.

**Updated:** Phase 1 now notes that SOC 2 evidence-collection can begin as
soon as its own Definition of Done is met, in parallel with Phases 2-5, not
strictly after them. Phase 6 still owns full Type I completion and SSO, but
the clock on SOC 2 itself can start much earlier than the phase number
suggests.

## 4. ERP bridges (Salesforce/NetSuite) were mis-prioritized

The deck's Q1 roadmap lists "Wire Salesforce / NetSuite bridges" as required
for the first pilots. The original roadmap filed generic ERP integration
under Phase 7 as a low-priority "integration marketplace" item. If real
design partners need a specific bridge to sign, that's revenue-blocking work,
not a post-launch nice-to-have.

**Updated:** Phase 2 now flags customer-specific ERP bridge work as real,
currently-unscheduled engineering effort that should be scoped per design
partner as pilots are signed — not deferred to Phase 7's generic integration
marketplace, which is a different (lower-priority, platform-wide) piece of
work.

## 5. Oracle Cloud — RESOLVED

Confirmed: Oracle Cloud is a $0/month Always-Free ARM VM used only as a
development sandbox, not part of a permanent dual-cloud plan. Single-cloud
AWS (eu-west-2 London: ECS Fargate, RDS, Connect/Lex/Lambda in one VPC) is
the confirmed funded target. The team-ask slide's "Oracle Cloud + AWS
migration" wording should be updated to something like: "Infrastructure &
Scale: migration from a free-tier development prototype to production-grade
AWS London infrastructure (ECS Fargate, RDS PostgreSQL, Amazon Connect UK DID
trunks) with single-VPC data residency" — so an investor reads it as a
funded upgrade path, not a permanent hybrid architecture.

**Updated:** Phase 0 now covers the free-tier bootstrap on Oracle Cloud +
Supabase explicitly, and Phase 1 is reframed as the funded migration to
AWS-native infrastructure.

## 6. Capacity reality check

Q1 alone, per the deck, asks for: 3 signed pilots, SOC 2 Type I readiness,
Salesforce/NetSuite bridges, and a first reference customer — while Phase 1's
infrastructure work (Postgres migration, secrets management, superadmin,
backups) is realistically 2-4 weeks of focused solo work on its own, and
you're simultaneously running the fundraise. This isn't a reason to change
the plan, but it's worth being honest that this is an aggressive quarter for
one person, and the two new hires this round funds don't land until after
the round closes — they can't help with Q1 itself.
