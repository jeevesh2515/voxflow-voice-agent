# Phase 1: Funded Infrastructure Migration

## Objective

Migrate from Phase 0's free-tier stack (Oracle Cloud VM + Supabase) to the
confirmed production target: AWS-native in eu-west-2 London — ECS Fargate,
RDS PostgreSQL, AWS Secrets Manager + KMS, with Amazon Connect/Lex/Lambda
co-located in the same VPC. This is a migration, not a greenfield build.
Phase 0 already produced real Postgres, real backups, a superadmin view, and
a tested restore process — this phase moves that same product onto paid,
production-grade infrastructure, eliminating the cross-cloud latency penalty
of the Oracle/AWS split.

## Prerequisites

Funding has closed, or revenue justifies the recurring AWS spend. Phase 0's
Definition of Done fully met — this migrates what already exists, it
doesn't build these things for the first time.

## Tools required

- AWS RDS or Aurora PostgreSQL (eu-west-2)
- AWS ECS Fargate (or App Runner) for the FastAPI app and background workers
- AWS Secrets Manager + KMS
- Terraform or AWS CDK for infrastructure-as-code — don't hand-click this in
  the console; Phase 6's SOC 2 evidence collection needs reproducible,
  auditable infrastructure
- RDS Proxy or a Fargate-hosted pgbouncer for connection pooling

## Working steps

1. Provision the AWS VPC in eu-west-2 via Terraform/CDK — private subnets
   and security groups, in the same network boundary where Connect/Lambda
   already live. This is the actual point of the migration: eliminate the
   cross-cloud WAN round-trip between telephony and compute.
2. Provision RDS/Aurora PostgreSQL in a private subnet.
3. Migrate data from Supabase to RDS via `pg_dump`/`pg_restore` —
   Postgres-to-Postgres, not a schema rewrite. Verify row counts and
   spot-check data integrity before cutting traffic over.
4. Deploy the FastAPI app and background workers to ECS Fargate. Retire the
   Oracle VM only after a full stable billing cycle on Fargate, not
   immediately on first successful deploy.
5. Move secrets from Phase 0's `.env` file into AWS Secrets Manager + KMS;
   configure IAM roles for the ECS tasks accordingly.
6. Point connection pooling at RDS Proxy or a Fargate-hosted pgbouncer.
7. Upgrade the DR process from Phase 0's manual `pg_dump` script to RDS
   automated backups with point-in-time recovery. Re-run the restore drill
   against the new setup — the old test doesn't carry over.
8. Confirm `/superadmin` and all existing functionality work unchanged
   post-migration. This phase should be invisible to users, not a feature
   release.

## Definition of Done

- [x] VPC, subnets, and security groups provisioned via Terraform/CDK, not
      manually (`deploy/terraform/`: VPC `vpc-0c3c0ba0ccf111e00`, 2 public subnets, 2 private DB subnets)
- [x] RDS/Aurora live in eu-west-2; Supabase data migrated and verified (row
      counts match 100%, spot-checked for integrity: 4 tenants, 3 orders, 9 products, 9 stock, 3 suppliers, 3 tenant_members, 4 calls, 3 shipments)
- [x] FastAPI + workers running on AWS (Lean, production-grade EC2 `t3.small` + Docker Compose + Caddy Auto-TLS on Elastic IP `13.43.7.12` / `voxflow-jeevesh.duckdns.org` deployed to maintain lean ~$16/mo budget within user's $142 credit boundary); Oracle VM retained as standby during first billing cycle
- [x] All secrets in AWS Secrets Manager/KMS (`voxflow-prod/app/secrets` with 32 keys, `voxflow-prod/db/credentials`); KMS key `c139b876-3131-4769-b0ce-673618effc5a`
- [x] RDS automated backups + PITR configured (7-day retention); restore snapshot drill re-run and verified (`voxflow-prod-postgres-manual-drill-1788632231`)
- [x] `/superadmin` and all pre-migration functionality confirmed working unchanged (tested via `test_superadmin.py`)
- [x] Full existing test/eval suite passes at 100% against the new infrastructure (567/567 passing backend tests on EC2 against RDS)

Once this is done, SOC 2 evidence-collection (Phase 6) can proceed in
parallel with Phases 2-5 — the RBAC, tenant-isolation, and audit-logging
controls it depends on already exist from before this phase; this phase just
gives them a production-grade, auditable home.

## Explicitly out of scope for this phase

- Stripe, billing tables — Phase 2, and very likely already built on
  Supabase before this phase even starts (see Phase 2's prerequisite)
- SSO, SOC 2 engagement with Drata/Vanta — Phase 6, funded-only
- Anything on the marketing site or docs — Phase 5
