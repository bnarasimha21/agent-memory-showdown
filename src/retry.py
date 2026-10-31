"""Retrying chat model calls on rate limits and server errors.

A long benchmark makes thousands of calls; one HTTP 429 or 5xx should cost a
short wait, not a failed run (a failed run drops that seed for the backend).
`invoke_with_retry` retries those, and connection errors and timeouts, with
exponential backoff and jitter. Anything else (a 400, a bad key) is raised at
once. The OpenAI client's own retries are switched off in src/llm_factory.py so
that the attempts counted here are all the attempts made.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

_TRANSIENT_NAMES = {"APIConnectionError", "APITimeoutError", "RateLimitError",
                    "InternalServerError", "ServiceUnavailableError", "Timeout", "ConnectTimeout",
                    "ReadTimeout", "ConnectError"}


def status_of(exc: BaseException) -> int | None:
    for obj in (exc, getattr(exc, "response", None)):
        code = getattr(obj, "status_code", None) if obj is not None else None
        if isinstance(code, int):
            return code
    return None


def is_transient(exc: BaseException) -> bool:
    code = status_of(exc)
    if code is not None:
        return code == 429 or code >= 500
    return type(exc).__name__ in _TRANSIENT_NAMES


def call_with_retry(fn: Callable[[], Any], what: str = "LLM call", max_retries: int | None = None,
                    base_delay: float | None = None, sleep: Callable[[float], None] | None = None,
                    ) -> tuple[Any, int, float]:
    """(result, retries, ms of the successful attempt). Backoff: base * 2**n, plus up to 25% jitter.

    The returned time covers the attempt that succeeded only, so waiting out a
    rate limit does not show up as model latency; the retry count is recorded
    separately.
    """
    from src.config import config

    max_retries = config.LLM_MAX_RETRIES if max_retries is None else max_retries
    base_delay = config.LLM_RETRY_BASE_S if base_delay is None else base_delay
    sleep = sleep or time.sleep
    attempt = 0
    while True:
        start = time.perf_counter()
        try:
            result = fn()
        except Exception as exc:
            if attempt >= max_retries or not is_transient(exc):
                raise
            delay = base_delay * (2 ** attempt)
            delay += random.uniform(0, delay * 0.25)
            logger.warning("%s failed (%s: %s); retry %d of %d in %.1fs", what, type(exc).__name__,
                           exc, attempt + 1, max_retries, delay)
            sleep(delay)
            attempt += 1
            continue
        return result, attempt, (time.perf_counter() - start) * 1000


def invoke_with_retry(model, messages, what: str = "LLM call"):
    """`model.invoke(messages)` with retries. Returns (message, retries, ms of the successful attempt)."""
    return call_with_retry(lambda: model.invoke(messages), what)
