"""Standalone, controlled Day 29 campaign worker process entrypoint."""

from __future__ import annotations

import logging

from ..config import get_settings
from ..db import SessionLocal
from .campaign_dispatch import CampaignDispatchHandler
from .staging import canary_tenant_ids, durable_campaign_worker_enabled
from .worker import WorkerRuntime

log = logging.getLogger(__name__)


def build_campaign_worker() -> WorkerRuntime | None:
    """Build a canary-scoped worker or return ``None`` while the kill switch is off."""

    settings = get_settings()
    allowed_tenants = canary_tenant_ids()
    if not durable_campaign_worker_enabled():
        log.warning("campaign_worker.staged reason=%s", "global_kill_switch_off")
        return None
    if not allowed_tenants:
        log.error("campaign_worker.staged reason=%s", "no_canary_tenants_configured")
        return None

    return WorkerRuntime(
        session_factory=SessionLocal,
        handlers={"campaign.target.dispatch": CampaignDispatchHandler()},
        pool_name="campaign-dispatch",
        job_types=("campaign.target.dispatch",),
        tenant_ids=allowed_tenants,
        batch_size=settings.durable_campaign_max_in_flight_per_tenant,
        max_concurrency=settings.durable_campaign_max_in_flight_per_tenant,
        lease_seconds=90,
        poll_interval_seconds=1.0,
    )


def main() -> None:
    """Run the worker only when deliberate canary activation is configured."""

    worker = build_campaign_worker()
    if worker is None:
        raise SystemExit("Campaign worker remains safely staged; enable an explicit canary to run it.")
    worker.run_forever()


if __name__ == "__main__":  # pragma: no cover - process entrypoint
    main()
