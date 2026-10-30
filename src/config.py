"""Configuration loaded from environment variables / .env file.

Values are read when `Config()` is created and again on `config.reload()`, so
tests can change the environment and reload instead of re-importing modules.
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _int_list(raw: str) -> list[int]:
    return [int(t) for t in raw.split(",") if t.strip()]


def _opt_int(raw: str | None) -> int | None:
    return int(raw) if raw not in (None, "") else None


class Config:
    def __init__(self) -> None:
        self.reload()

    def reload(self) -> "Config":
        env = os.getenv

        # LLM provider: "do" (DigitalOcean Serverless Inference, OpenAI-compatible,
        # paid) or "fake" (deterministic offline model in src/fakes.py, free).
        self.LLM_PROVIDER: str = env("LLM_PROVIDER", "do").strip().lower()

        # DigitalOcean Serverless Inference
        self.DO_API_KEY: str = env("DO_API_KEY", "")
        self.DO_INFERENCE_URL: str = env("DO_INFERENCE_URL", "https://inference.do-ai.run/v1")

        # LLM (Claude via DO Serverless Inference)
        self.LLM_MODEL: str = env("LLM_MODEL", "anthropic-claude-4.5-sonnet")

        # Embeddings: "local" = sentence-transformers on CPU, "fake" = deterministic
        # hashing embedding (src/fakes.py). The dimension must match the model
        # output (all-MiniLM-L6-v2 = 384).
        self.EMBEDDING_PROVIDER: str = env("EMBEDDING_PROVIDER", "local").strip().lower()
        self.EMBEDDING_MODEL: str = env("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        self.EMBEDDING_DIMENSION: int = int(env("EMBEDDING_DIMENSION", "384"))

        # Retrieval depth for vector backends
        self.RETRIEVAL_K: int = int(env("RETRIEVAL_K", "4"))

        # Fake LLM knobs (only used when LLM_PROVIDER=fake). Unset token values
        # mean "count whitespace-separated words of the prompt / reply".
        self.FAKE_LLM_SLEEP_MS: float = float(env("FAKE_LLM_SLEEP_MS", "0") or 0)
        self.FAKE_LLM_INPUT_TOKENS: int | None = _opt_int(env("FAKE_LLM_INPUT_TOKENS"))
        self.FAKE_LLM_OUTPUT_TOKENS: int | None = _opt_int(env("FAKE_LLM_OUTPUT_TOKENS"))
        self.FAKE_SUMMARY_MAX_SENTENCES: int = int(env("FAKE_SUMMARY_MAX_SENTENCES", "8"))

        # Vector DBs
        self.QDRANT_URL: str = env("QDRANT_URL", "http://localhost:6333")
        self.POSTGRES_HOST: str = env("POSTGRES_HOST", "localhost")
        self.POSTGRES_PORT: int = int(env("POSTGRES_PORT", "5432"))
        self.POSTGRES_USER: str = env("POSTGRES_USER", "benchmark")
        self.POSTGRES_PASSWORD: str = env("POSTGRES_PASSWORD", "benchmark")
        self.POSTGRES_DB: str = env("POSTGRES_DB", "memory_bench")

        # Benchmark parameters
        self.NUM_RUNS: int = int(env("NUM_RUNS", "5"))
        self.NUM_TURNS: int = int(env("NUM_TURNS", "50"))
        self.BASE_SEED: int = int(env("BASE_SEED", "42"))
        self.SEED_TURNS: list[int] = _int_list(
            env("SEED_TURNS", "1,3,7,12,18,25,30,35,40,45")
        )
        # CHECKPOINTS replaces RECALL_TURNS. A checkpoint N means "after turn N,
        # probe every fact planted so far against a read-only memory snapshot".
        checkpoints = env("CHECKPOINTS")
        if checkpoints is None and env("RECALL_TURNS") is not None:
            logger.warning("RECALL_TURNS is deprecated; use CHECKPOINTS instead")
            checkpoints = env("RECALL_TURNS")
        self.CHECKPOINTS: list[int] = _int_list(checkpoints or "15,25,35,50")

        # Output
        self.RESULTS_DIR: str = env("RESULTS_DIR", "results")
        return self

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def postgres_sqlalchemy_url(self) -> str:
        """SQLAlchemy URL with the driver named explicitly.

        SQLAlchemy 2.1 made psycopg (v3) the default for bare `postgresql://`,
        but the community PGVector store only works with psycopg2.
        """
        return self.postgres_dsn.replace("postgresql://", "postgresql+psycopg2://", 1)


config = Config()
