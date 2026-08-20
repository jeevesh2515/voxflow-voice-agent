"""Tests for controlled standalone campaign worker activation."""

from __future__ import annotations

from types import SimpleNamespace

from voxflow_api.jobs import campaign_worker_service
from voxflow_api.jobs.worker import WorkerRuntime


def test_worker_is_not_constructed_when_global_kill_switch_is_off(monkeypatch):
    monkeypatch.setattr(campaign_worker_service, "durable_campaign_worker_enabled", lambda: False)
    monkeypatch.setattr(campaign_worker_service, "canary_tenant_ids", lambda: ("varun",))

    assert campaign_worker_service.build_campaign_worker() is None


def test_worker_is_not_constructed_without_an_explicit_canary_tenant(monkeypatch):
    monkeypatch.setattr(campaign_worker_service, "durable_campaign_worker_enabled", lambda: True)
    monkeypatch.setattr(campaign_worker_service, "canary_tenant_ids", lambda: ())

    assert campaign_worker_service.build_campaign_worker() is None


def test_worker_is_scoped_to_explicit_canary_tenant_and_dispatch_job_type(monkeypatch):
    monkeypatch.setattr(campaign_worker_service, "durable_campaign_worker_enabled", lambda: True)
    monkeypatch.setattr(campaign_worker_service, "canary_tenant_ids", lambda: ("varun",))
    monkeypatch.setattr(
        campaign_worker_service,
        "get_settings",
        lambda: SimpleNamespace(durable_campaign_max_in_flight_per_tenant=2),
    )

    worker = campaign_worker_service.build_campaign_worker()

    assert isinstance(worker, WorkerRuntime)
    assert worker.job_types == ("campaign.target.dispatch",)
    assert worker.tenant_ids == ("varun",)
    assert worker.batch_size == 2
    assert worker.max_concurrency == 2
