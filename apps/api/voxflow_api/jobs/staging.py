"""Safe activation controls for the durable campaign worker rollout."""

from __future__ import annotations

import os


def durable_campaign_worker_enabled() -> bool:
    """Return whether the independently deployed campaign worker is enabled.

    The default is deliberately false. Day 28 stages campaign intent and
    operator visibility only; Day 29 will enable the worker after its deployment
    and callback reconciliation path have passed a controlled rollout.
    """

    return os.getenv("DURABLE_CAMPAIGN_WORKER_ENABLED", "false").strip().lower() in {"1", "true", "yes"}


def campaign_activation_mode() -> str:
    """Expose a non-sensitive rollout state for the operator dashboard."""

    return "enabled" if durable_campaign_worker_enabled() else "staged"
