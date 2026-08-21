"""Design-partner and controlled-pilot readiness evidence.

The scorecard is deliberately diagnostic. It cannot approve a pilot, create a
recipient cohort, enable a worker, configure a provider, or send an invitation.
Human-owned commercial, legal, telecom, consent, and coverage gates remain
blocked until supplied through a separate reviewed process.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from .config import get_settings
from .db import TenantMember, TenantPrivacyPolicy
from .jobs.staging import durable_campaign_dry_run, durable_side_effects_dry_run
from .pilot_readiness import pilot_scorecard
from .reliability import reliability_scorecard


def _gate(code: str, category: str, status: str, owner: str, detail: str) -> dict[str, str]:
    return {"code": code, "category": category, "status": status, "owner": owner, "detail": detail}


def design_partner_readiness(db: Session, tenant_id: str) -> dict[str, object]:
    """Build a redacted evidence scorecard without any state transition."""

    settings = get_settings()
    memberships = (
        db.query(TenantMember)
        .filter(TenantMember.tenant_id == tenant_id, TenantMember.status == "active")
        .all()
    )
    owner_count = sum(1 for member in memberships if member.role == "owner")
    policy_exists = db.get(TenantPrivacyPolicy, tenant_id) is not None
    reliability = reliability_scorecard(db, tenant_id=tenant_id)
    pilot = pilot_scorecard(db, tenant_id=tenant_id)
    worker_safe = (
        not settings.durable_campaign_worker_enabled
        and durable_campaign_dry_run()
        and not settings.durable_side_effects_worker_enabled
        and durable_side_effects_dry_run()
    )

    gates = [
        _gate(
            "tenant_membership_boundary",
            "software",
            "ready" if owner_count >= 1 else "blocked",
            "VoxFlow platform owner",
            "At least one active tenant owner must exist in the application-owned membership ledger.",
        ),
        _gate(
            "privacy_retention_policy",
            "software",
            "ready" if policy_exists else "attention",
            "Tenant owner",
            "Retention settings can be recorded, but export and deletion remain human-reviewed only.",
        ),
        _gate(
            "simulation_safety_posture",
            "software",
            "ready" if worker_safe else "blocked",
            "VoxFlow platform owner",
            "Campaign and side-effect workers must remain disabled and dry-run; no provider dispatch is permitted.",
        ),
        _gate(
            "reliability_evidence",
            "software",
            "ready" if reliability.get("overall_status") == "healthy" else "attention",
            "VoxFlow engineering",
            "SLO scorecards, deterministic drill receipts, and recovery previews must be reviewed before any pilot discussion.",
        ),
        _gate(
            "customer_authority",
            "human",
            "blocked",
            "Design partner",
            "A signed customer authorization and named operational owner are required outside this application.",
        ),
        _gate(
            "recipient_consent_and_cohort",
            "human",
            "blocked",
            "Design partner",
            "A verified limited recipient cohort, consent evidence, and opt-out handling must be reviewed before outreach.",
        ),
        _gate(
            "telecom_provider_registration",
            "human_and_paid_provider",
            "blocked",
            "Telecom provider administrator",
            "No telecom registration, provider subscription, callback secret, or provider activation is performed by this free-tier MVP.",
        ),
        _gate(
            "human_escalation_coverage",
            "human",
            "blocked",
            "Design partner",
            "Named human escalation coverage, operating hours, and rollback authority require a reviewed external runbook.",
        ),
        _gate(
            "production_hosting_and_support",
            "human_and_paid_infrastructure",
            "blocked",
            "VoxFlow platform owner",
            "Render Free and Vercel Hobby are demonstration environments, not a production operating commitment.",
        ),
        _gate(
            "authenticated_customer_websocket",
            "software",
            "blocked",
            "VoxFlow engineering",
            "The browser simulator is confined to the fixed demo tenant until an authenticated WebSocket handshake is implemented.",
        ),
    ]
    blocked = [gate for gate in gates if gate["status"] == "blocked"]
    attention = [gate for gate in gates if gate["status"] == "attention"]
    return {
        "tenant_id": tenant_id,
        "status": "blocked" if blocked else ("attention" if attention else "ready_for_human_review"),
        "summary": {
            "active_membership_count": len(memberships),
            "active_owner_count": owner_count,
            "reliability_status": reliability.get("overall_status"),
            "pilot_admission_status": pilot.get("status"),
            "campaign_worker_enabled": settings.durable_campaign_worker_enabled,
            "side_effect_worker_enabled": settings.durable_side_effects_worker_enabled,
            "provider_activity_enabled": False,
        },
        "gates": gates,
        "automatic_activation": False,
        "next_step": "Review every blocked human-owned gate outside the application; do not enable providers or workers from this scorecard.",
    }
