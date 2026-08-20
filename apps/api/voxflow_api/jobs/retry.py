"""Retry classification and full-jitter delay calculation for durable jobs."""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime
from typing import Callable


class JobExecutionError(Exception):
    """Base class for a handler outcome that should become durable job state."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(detail or code)
        self.code = code
        self.detail = detail


class RetryableJobError(JobExecutionError):
    """A transient failure that may be scheduled for another attempt."""

    def __init__(self, code: str, detail: str = "", retry_after_seconds: float | None = None) -> None:
        super().__init__(code, detail)
        self.retry_after_seconds = retry_after_seconds


class PermanentJobError(JobExecutionError):
    """A terminal validation, policy, or configuration error."""


class PolicyCancelledJobError(PermanentJobError):
    """A policy denial that is terminal, auditable, and not a dead letter."""


class PolicyDeferredJobError(JobExecutionError):
    """A policy delay with an exact durable eligibility boundary."""

    def __init__(self, code: str, *, next_eligible_at: datetime, detail: str = "") -> None:
        super().__init__(code, detail)
        self.next_eligible_at = next_eligible_at


@dataclass(frozen=True)
class RetryDecision:
    """The selected retry delay and the policy source that selected it."""

    delay_seconds: float
    source: str


def full_jitter_delay(
    attempt: int,
    *,
    base_seconds: float = 5.0,
    max_seconds: float = 900.0,
    random_value: Callable[[], float] = random.random,
) -> float:
    """Return full-jitter exponential backoff for a one-indexed attempt.

    The result is uniform from zero through ``min(max_seconds,
    base_seconds * 2 ** (attempt - 1))``. Injecting ``random_value`` makes the
    calculation deterministic in tests.
    """

    if attempt < 1:
        raise ValueError("attempt must be at least 1")
    if base_seconds <= 0:
        raise ValueError("base_seconds must be positive")
    if max_seconds <= 0:
        raise ValueError("max_seconds must be positive")

    cap = min(max_seconds, base_seconds * (2 ** (attempt - 1)))
    value = random_value()
    if not 0 <= value <= 1:
        raise ValueError("random_value must return a number in [0, 1]")
    return cap * value


def retry_decision(
    attempt: int,
    *,
    retry_after_seconds: float | None = None,
    base_seconds: float = 5.0,
    max_seconds: float = 900.0,
    random_value: Callable[[], float] = random.random,
) -> RetryDecision:
    """Use a provider-specified delay when present, otherwise full jitter."""

    if retry_after_seconds is not None:
        if retry_after_seconds < 0:
            raise ValueError("retry_after_seconds must be non-negative")
        return RetryDecision(delay_seconds=min(retry_after_seconds, max_seconds), source="provider")
    return RetryDecision(
        delay_seconds=full_jitter_delay(
            attempt,
            base_seconds=base_seconds,
            max_seconds=max_seconds,
            random_value=random_value,
        ),
        source="full_jitter",
    )
