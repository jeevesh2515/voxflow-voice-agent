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

## Security Best Practices for Self-Hosting

When deploying VoxFlow Voice Agent in staging or production environments:
- **Never commit `.env` files** containing live API keys, database credentials, or signing secrets.
- Always use encrypted database backups (`scripts/db_backup.sh`) with strong `BACKUP_ENCRYPTION_KEY` passphrases.
- Restrict database ingress to the session pooler and enforce Row Level Security (RLS).
- Rotate webhook HMAC secrets (`CONNECT_LAMBDA_SECRET`, `DIAL_CALLBACK_SHARED_SECRET`) periodically.
