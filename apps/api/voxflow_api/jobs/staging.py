"""Safe activation controls for the durable campaign worker rollout."""

from __future__ import annotations

from ..config import get_settings


def durable_campaign_worker_enabled() -> bool:
    """Return whether the independently deployed campaign worker is globally enabled."""

    return get_settings().durable_campaign_worker_enabled


def canary_tenant_ids() -> tuple[str, ...]:
    """Return the explicit tenant allow-list permitted to receive worker claims."""

    return get_settings().durable_campaign_canary_tenant_ids


def durable_campaign_dry_run() -> bool:
    """Return whether provider calls are simulated while recording full intent."""

    return get_settings().durable_campaign_dry_run


def durable_side_effects_worker_enabled() -> bool:
    """Return whether the separately deployed Day 34 worker may claim jobs."""

    return get_settings().durable_side_effects_worker_enabled


def side_effects_tenant_ids() -> tuple[str, ...]:
    """Return the explicit tenant allow-list for Day 34 integration work."""

    return get_settings().durable_side_effects_allowed_tenant_ids


def durable_side_effects_dry_run() -> bool:
    """Return whether the Day 34 worker records evidence without external IO."""

    return get_settings().durable_side_effects_dry_run


def side_effects_activation_mode() -> str:
    """Expose a non-sensitive Day 34 rollout state for read-only operators."""

    if not durable_side_effects_worker_enabled():
        return "staged"
    if not side_effects_tenant_ids():
        return "blocked"
    return "dry_run" if durable_side_effects_dry_run() else "canary"


def campaign_activation_mode() -> str:
    """Expose a non-sensitive rollout state for the operator dashboard."""

    if not durable_campaign_worker_enabled():
        return "staged"
    return "dry_run" if durable_campaign_dry_run() else "canary"
