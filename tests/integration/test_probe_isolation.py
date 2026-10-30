"""Issue 1: probes read memory without changing it, for every backend, on real services."""

import pytest

from src.backends.registry import AVAILABLE_BACKENDS
from src.dataset import SEEDED_FACTS
from src.harness import run_benchmark
from tests.helpers import group, records

pytestmark = pytest.mark.integration

BACKENDS = ["buffer", "summary", "qdrant", "pgvector"]
EXPECTED_UNITS = {"buffer": "messages", "summary": "summary_chars", "qdrant": "points",
                  "pgvector": "rows"}


def test_checkpoints_leave_memory_unchanged_and_see_only_the_past(services, tmp_path):
    bundle = run_benchmark(
        [AVAILABLE_BACKENDS[b] for b in BACKENDS],
        num_runs=1, num_turns=20, checkpoints=[10, 20], results_dir=tmp_path,
    )
    ends = records(bundle, "run_end")
    assert {e["backend"]: e["error"] for e in ends} == {b: None for b in BACKENDS}

    checkpoints = group(records(bundle, "checkpoint"), "backend")
    for backend in BACKENDS:
        cps = checkpoints[backend]
        assert [c["checkpoint"] for c in cps] == [10, 20]
        for cp in cps:
            assert cp["memory_before"] == cp["memory_after"], (backend, cp)
            assert cp["memory_before"]["unit"] == EXPECTED_UNITS[backend]
            assert cp["memory_before"]["size"] > 0
        # memory keeps growing between checkpoints, so the size check is meaningful
        assert cps[1]["memory_before"]["digest"] != cps[0]["memory_before"]["digest"]

    later_facts = [info["fact"] for turn, info in SEEDED_FACTS.items() if 10 < turn <= 20]
    assert later_facts, "fixture needs a fact planted between turn 10 and 20"
    probes = records(bundle, "probe")
    for p in probes:
        if p["checkpoint"] == 10:
            assert not any(f in p["context"] for f in later_facts), p
    for backend in BACKENDS:
        mine = [p for p in probes if p["backend"] == backend]
        assert len([p for p in mine if p["checkpoint"] == 10]) == 3  # turns 1, 3, 7
        assert len([p for p in mine if p["checkpoint"] == 20]) == 5  # + 12, 18
        assert all(p["write_ms"] == 0 and p["write_llm_calls"] == 0 for p in mine)


def test_vector_backends_retrieve_the_planted_fact(services, tmp_path):
    bundle = run_benchmark(
        [AVAILABLE_BACKENDS["qdrant"], AVAILABLE_BACKENDS["pgvector"]],
        num_runs=1, num_turns=10, checkpoints=[10], results_dir=tmp_path,
    )
    assert all(e["error"] is None for e in records(bundle, "run_end"))
    dog = [p for p in records(bundle, "probe") if p["fact_id"] == "dog_name"]
    assert {p["backend"] for p in dog} == {"qdrant", "pgvector"}
    for p in dog:
        assert "Baxter" in p["context"] and "Baxter" in p["response"], p
