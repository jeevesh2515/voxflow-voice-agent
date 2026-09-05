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

| Phase | Objective | Scope & Architecture | Status |
|---|---|---|---|
| **Phase 1** | Funded Infrastructure Migration | AWS RDS PostgreSQL 15.19, EC2 t3.small, Secrets Manager + KMS, Caddy Auto-TLS in eu-west-2 | ✅ Complete |
| **Phase 2** | Revenue Infrastructure (Stripe) | Stripe metered billing, automated invoicing, customer portal, webhook lifecycle | 🚀 Up Next |
| **Phase 3** | Operational Trust & Observability | Sentry telemetry, automated alerting, SQS DLQ redrive, high-durability logging | Planned |
| **Phase 4** | Legal & Compliance Baseline | GDPR/HIPAA compliance, DPA templates, automated data retention purges, audit trails | Planned |
| **Phase 5** | Go-to-Market Surface | Developer docs, interactive onboarding, self-serve tenant provisioning | Planned |
| **Phase 6** | Enterprise Readiness | Enterprise SSO (SAML/Okta), SOC 2 Type I readiness, Multi-AZ high availability | Planned |
| **Phase 7** | Scale & Retention | Enterprise integration marketplace (SAP/NetSuite/Salesforce), SLA guarantees | Planned |

Phase 1 is complete and running live in AWS eu-west-2 (London): VPC `vpc-0c3c0ba0ccf111e00`, AWS RDS PostgreSQL 15.19 (`db.t4g.micro`, KMS encrypted), EC2 `t3.small` (`13.43.7.12`), Caddy Auto-TLS (`https://voxflow-jeevesh.duckdns.org`), AWS Secrets Manager (32 app keys + DB credentials), and 7-day PITR automated backups. Phase 2 (Stripe Revenue Infrastructure) is the active next phase.

