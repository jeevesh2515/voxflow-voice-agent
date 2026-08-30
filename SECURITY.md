# Security Policy

## Supported Versions

We actively provide security patches and updates for the following versions of VoxFlow Voice Agent:

| Version | Supported | Notes |
|---|---|---|
| `0.1.x` (main) | :white_check_mark: | Active development & production branch |
| `< 0.1.0` | :x: | Legacy preview releases |

---

## Reporting a Vulnerability

The VoxFlow security team takes all vulnerability reports seriously. If you believe you have discovered a security issue, please follow responsible disclosure guidelines.

### How to Report

**Please DO NOT report security vulnerabilities through public GitHub issues, discussions, or social channels.**

Instead, report vulnerabilities privately by:
1. **GitHub Security Advisory:** Submit a private report via the [GitHub Security Advisories](https://github.com/jeevesh2515/voxflow-voice-agent/security/advisories/new) page.
2. **Direct Email:** Email the core maintainer directly at `contact@voxflow.ai` or `jeevesh2515@gmail.com` with the subject line `[SECURITY DISCLOSURE] VoxFlow Vulnerability Report`.

### Information to Include

Please include as much of the following details as possible to help us triage and resolve the issue quickly:
- **Type of issue:** (e.g. Authentication bypass, SQL injection, RCE, IDOR, SSRF, Information disclosure)
- **Component affected:** (e.g. `apps/api/voxflow_api/routes/connect.py`, `apps/api/voxflow_api/db.py`, etc.)
- **Step-by-step reproduction:** Proof-of-concept scripts or curl commands demonstrating the vulnerability.
- **Impact:** Potential impact on confidentiality, integrity, or availability.
- **Suggested remediation:** Proposed fixes or patches, if known.

---

## Response & Disclosure Process

1. **Acknowledgment:** We will acknowledge receipt of your vulnerability report within **24–48 hours**.
2. **Assessment:** Our engineering team will validate and assess the vulnerability severity within **3 business days**.
3. **Remediation:** A patch will be authored, reviewed, and tested against our CI test suite.
4. **Release:** We will publish a security fix and release notes acknowledging your contribution (unless you prefer anonymity).

---

## UK GDPR & Data Protection Act 2018 Compliance Architecture

VoxFlow is designed to pass UK enterprise procurement security and data-protection audits.

- **Lawful basis & data minimisation**: Only caller phone/name, transcript, and escalation metadata required for supply-chain voice operations are stored per-tenant. Financial order refs are never anonymized (legal accounting invariant).
- **Retention by default**: `call_retention_days` (90) and `transcript_retention_days` (30) per tenant; automated purge scrubs `transcript_json`/`reason`/`solution` and anonymizes session records when `created_at < now() - retention_days`.
- **DSR handling**: Right of Access (DSAR export) and Right to Erasure are server-authoritative, tenant-isolated, and gated by RBAC (export: owner/operator; erasure: owner + `DELETE DATA` token). SLA: < 30 days.
- **Audit trail**: Every purge and erasure creates an immutable `retention_purge_logs` receipt (`records_scanned`, `calls_anonymized`, `transcripts_purged`, `dry_run`, `execution_type`).

## PII Data Flow & Encryption Standards

- **In transit**: TLS 1.3 (HTTPS + WSS) for all browser, API, and webhook traffic.
- **At rest**: AES-256 (Supabase/Postgres encrypted volumes + encrypted backups).
- **PII masking**: When `pii_masking_enabled=1`, external exports (Google Sheets mirror, webhooks) mask phones (`+44 7911 *** 456`) and emails (`j***e@acme.co.uk`) via `privacy_service.mask_*`.
- **Backups**: GPG-encrypted automated snapshots (`scripts/db_backup.sh`); verification restores tested quarterly.

## Authorized Sub-Processors & Data Residency

| Sub-Processor | Purpose | Data Residency |
|---|---|---|
| AWS (Connect, Lex, Polly) | Telephony & voice AI | EU / London (`eu-west-2`) |
| Groq | LLM inference | Zero Data Retention (ZDR) |
| Supabase | PostgreSQL primary store | London `eu-west-2` |
| Google Workspace | Sheets mirror (per-tenant) | Customer-owned spreadsheet |

Primary data residency: `eu-west-2` (London). `tenants.data_residency_region` records residency per tenant.

## Data Subject Request (DSR) Handling Protocol & SLA

1. Subject contacts tenant owner via privacy dashboard (`/dashboard/privacy` → phone/email lookup).
2. Owner/operator generates DSAR export (`POST /api/tenants/{id}/privacy/export`) — tenant-isolated JSON bundle.
3. Owner executes erasure (`POST /api/tenants/{id}/privacy/erase` with `DELETE DATA`) — atomically redacts calls/escalations/communications/supplier contacts.
4. All DSRs completed within **30 days**; purge cron runs retention windows daily.

## Backup & Disaster Recovery Verification

- Automated snapshots GPG-encrypted with `BACKUP_ENCRYPTION_KEY`.
- Quarterly restore drill verified and logged; RPO 24h, RTO 4h.

## Security Best Practices for Self-Hosting

When deploying VoxFlow Voice Agent in staging or production environments:
- **Never commit `.env` files** containing live API keys, database credentials, or signing secrets.
- Always use encrypted database backups (`scripts/db_backup.sh`) with strong `BACKUP_ENCRYPTION_KEY` passphrases.
- Restrict database ingress to the session pooler and enforce Row Level Security (RLS).
- Rotate webhook HMAC secrets (`CONNECT_LAMBDA_SECRET`, `DIAL_CALLBACK_SHARED_SECRET`) periodically.
- Apply migration `016_telephony_routing_and_caller_pins.sql` before deploying exact-DID routing and verify unknown/inactive DIDs fail closed.
- Never seed predictable production caller PINs. Set per-contact 4–8 digit values through the authenticated owner workflow; do not log, export, or return plaintext PINs or verifier hashes.
- Apply migration `021_tenant_data_retention.sql` and set per-tenant retention windows appropriate to your DPA; verify `pii_masking_enabled` for external exports.
