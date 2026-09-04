"""Shared transient/permanent error classification + retry (API side).

Mirrors the retry layer deployed with the recording Lambda
(deploy/aws/s3_recordings_handler.py) so both sides of the pipeline classify
failures identically:

- transient (retryable): Stripe HTTP 429 or 5xx, connection errors, timeouts
- permanent: Stripe HTTP 4xx (invalid_api_key, resource_missing, ...)

Retries use exponential backoff + jitter. Permanent errors are raised
immediately so the caller can surface them instead of burning retry budget.
"""

from __future__ import annotations

import functools
import random
import socket
import time
from typing import Any, Callable

TRANSIENT_CODES = frozenset({429, 500, 502, 503, 504})


def classify_error(exc: BaseException) -> str:
    """Return 'transient' (retryable) or 'permanent' (stop retrying)."""
    http_status = getattr(exc, "http_status", None)  # Stripe APIError family
    if http_status is not None:
        try:
            status = int(http_status)
        except (TypeError, ValueError):
            status = 0
        if status in TRANSIENT_CODES:
            return "transient"
        if 400 <= status < 500:
            return "permanent"
        # Stripes: 3xx shouldn't happen; anything non-4xx retries.
        return "transient"
    if isinstance(exc, (ConnectionError, TimeoutError, socket.timeout, OSError)):
        return "transient"
    # Unknown exception type: retry it (safe default - never silently drop
    # billable usage); the caller's billed-flag prevents double-charging.
    return "transient"


def is_transient_error(exc: BaseException) -> bool:
    return classify_error(exc) == "transient"


def retry_transient(
    tries: int = 3, base_delay: float = 0.5, max_delay: float = 8.0, jitter: float = 0.3
) -> Callable:
    """Retry a function only on transient errors, with exp. backoff + jitter."""

    def deco(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last: BaseException | None = None
            for attempt in range(1, tries + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001
                    last = exc
                    if not is_transient_error(exc):
                        raise
                    if attempt == tries:
                        break
                    delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                    delay *= 1.0 + random.uniform(0, jitter)
                    time.sleep(delay)
            assert last is not None
            raise last

        return wrapper

    return deco
