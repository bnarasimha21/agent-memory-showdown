"""Integration tests need the compose Qdrant and Postgres (`make test-integration`).

When AMS_REQUIRE_SERVICES=1 (set by the make target) an unreachable service is
a failure; otherwise the integration tests are skipped with the reason.
"""

from __future__ import annotations

import os
import time
import urllib.request

import psycopg2
import pytest

from src.config import config


def _qdrant_ready() -> str | None:
    try:
        with urllib.request.urlopen(f"{config.QDRANT_URL}/readyz", timeout=2) as resp:
            return None if resp.status == 200 else f"qdrant status {resp.status}"
    except Exception as exc:
        return f"qdrant at {config.QDRANT_URL}: {exc}"


def _postgres_ready() -> str | None:
    try:
        conn = psycopg2.connect(config.postgres_dsn, connect_timeout=2)
        conn.close()
        return None
    except Exception as exc:
        return f"postgres at {config.POSTGRES_HOST}:{config.POSTGRES_PORT}: {exc}"


@pytest.fixture(scope="session")
def services():
    deadline = time.time() + (60 if os.environ.get("AMS_REQUIRE_SERVICES") else 3)
    while True:
        problems = [p for p in (_qdrant_ready(), _postgres_ready()) if p]
        if not problems or time.time() > deadline:
            break
        time.sleep(1)
    if problems:
        message = "compose services unavailable: " + "; ".join(problems)
        if os.environ.get("AMS_REQUIRE_SERVICES"):
            pytest.fail(message)
        pytest.skip(message)
    return config

