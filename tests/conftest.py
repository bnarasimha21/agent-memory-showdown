"""Test environment: always the offline fake LLM and fake embeddings.

This runs before any `src` module is imported by a test, and forces settings
so no test can reach a paid API even if a developer's .env sets DO_API_KEY.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FORCED_ENV = {
    "LLM_PROVIDER": "fake",
    "EMBEDDING_PROVIDER": "fake",
    "JUDGE_PROVIDER": "fake",
    "DO_API_KEY": "",
    "EMBEDDING_DIMENSION": "384",
    "QDRANT_URL": os.environ.get("AMS_TEST_QDRANT_URL", "http://localhost:16333"),
    "POSTGRES_HOST": os.environ.get("AMS_TEST_POSTGRES_HOST", "localhost"),
    "POSTGRES_PORT": os.environ.get("AMS_TEST_POSTGRES_PORT", "15432"),
    "POSTGRES_USER": "benchmark",
    "POSTGRES_PASSWORD": "benchmark",
    "POSTGRES_DB": "memory_bench",
}
for _key in ("FAKE_LLM_SLEEP_MS", "FAKE_LLM_INPUT_TOKENS", "FAKE_LLM_OUTPUT_TOKENS",
             "CHECKPOINTS", "RECALL_TURNS", "SEED_TURNS", "RETRIEVAL_K", "NUM_RUNS",
             "NUM_TURNS", "BASE_SEED", "RESULTS_DIR", "JUDGE", "JUDGE_MODEL",
             "PRICING_FILE", "LLM_MAX_RETRIES", "LLM_RETRY_BASE_S"):
    os.environ.pop(_key, None)
os.environ.update(FORCED_ENV)

from src.config import config  # noqa: E402

config.reload()


@pytest.fixture
def fresh_config(monkeypatch):
    """Change env vars inside a test, then call fresh_config() to apply them."""

    def apply():
        return config.reload()

    yield apply
    monkeypatch.undo()  # restore the environment before reloading from it
    config.reload()
