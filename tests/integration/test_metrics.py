"""Issue 3: latency components and cost from fixed fake token usage."""

import json

import pytest

from src.backends.registry import AVAILABLE_BACKENDS
from src.harness import run_benchmark
from src.pricing import price_for

pytestmark = pytest.mark.integration

SLEEP_MS = 15
IN_TOK, OUT_TOK = 200, 20
BACKENDS = ["buffer", "summary", "qdrant", "pgvector"]


def test_latency_split_and_cost(services, tmp_path, monkeypatch, fresh_config):
    monkeypatch.setenv("FAKE_LLM_SLEEP_MS", str(SLEEP_MS))
    monkeypatch.setenv("FAKE_LLM_INPUT_TOKENS", str(IN_TOK))
    monkeypatch.setenv("FAKE_LLM_OUTPUT_TOKENS", str(OUT_TOK))
    fresh_config()
    bundle = run_benchmark([AVAILABLE_BACKENDS[b] for b in BACKENDS], num_runs=1, num_turns=10,
                           checkpoints=[10], results_dir=tmp_path, judge=False,
                           composition={"extraction": 2, "abstention": 1})
    agg = json.loads((bundle / "aggregate.json").read_text())
    price = price_for("fake-memory-v1")
    for name in BACKENDS:
        b = agg["backends"][name]
        assert "error" not in b, b
        lat = b["latency"]
        assert lat["llm_ms"]["p50"] >= SLEEP_MS and lat["llm_ms"]["p95"] >= lat["llm_ms"]["p50"]
        assert b["probe_latency"]["llm_ms"]["p50"] >= SLEEP_MS
        assert b["probe_latency"]["write_ms"]["p95"] == 0
        if name in ("qdrant", "pgvector"):
            assert lat["retrieve_ms"]["p50"] > 0
            assert b["memory_size_end"]["mean"] == 10
        # the summarizer is one extra LLM call per turn, counted as memory maintenance
        calls = 10 * (2 if name == "summary" else 1)
        assert b["tokens"]["memory"]["calls"] == (10 if name == "summary" else 0)
        if name == "summary":
            assert lat["write_ms"]["p50"] >= SLEEP_MS
        expected = calls * (IN_TOK * price.input_per_mtok + OUT_TOK * price.output_per_mtok) / 1e6
        assert b["cost"]["per_conversation_usd"] == pytest.approx(expected)
        assert b["tokens"]["input_tokens"] == calls * IN_TOK
        assert b["tokens"]["output_tokens"] == calls * OUT_TOK
