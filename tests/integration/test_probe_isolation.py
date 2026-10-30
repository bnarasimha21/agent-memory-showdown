"""Issue 1: probes read memory without changing it, for every backend, on real services."""

import json

import pytest

from src.backends.registry import AVAILABLE_BACKENDS
from src.harness import run_benchmark
from src.scoring.matcher import match_record
from tests.helpers import group, records

pytestmark = pytest.mark.integration

BACKENDS = ["buffer", "summary", "qdrant", "pgvector"]
EXPECTED_UNITS = {"buffer": "messages", "summary": "summary_chars", "qdrant": "points",
                  "pgvector": "rows"}


def test_checkpoints_leave_memory_unchanged_and_see_only_the_past(services, tmp_path):
    bundle = run_benchmark(
        [AVAILABLE_BACKENDS[b] for b in BACKENDS],
        num_runs=1, num_turns=20, checkpoints=[10, 20], results_dir=tmp_path,
        composition={"extraction": 3, "update": 1, "multi_hop": 1},
    )
    ds = json.loads((bundle / "dataset.json").read_text())["0"]
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

    later = [s["text"] for f in ds["facts"] for s in f["statements"] if 10 < s["turn"] <= 20]
    assert later, "fixture needs a fact stated between turn 10 and 20 (seed 42)"
    ready = {cp: sum(f["turn"] <= cp for f in ds["facts"]) for cp in (10, 20)}
    assert 0 < ready[10] < ready[20]
    probes = records(bundle, "probe")
    for p in probes:
        if p["checkpoint"] == 10:
            assert not any(text in p["context"] for text in later), p
    for backend in BACKENDS:
        mine = [p for p in probes if p["backend"] == backend]
        assert len([p for p in mine if p["checkpoint"] == 10]) == ready[10]
        assert len([p for p in mine if p["checkpoint"] == 20]) == ready[20]
        assert all(p["write_ms"] == 0 and p["write_llm_calls"] == 0 for p in mine)


def test_vector_backends_retrieve_the_planted_fact(services, tmp_path):
    bundle = run_benchmark(
        [AVAILABLE_BACKENDS["qdrant"], AVAILABLE_BACKENDS["pgvector"]],
        num_runs=1, num_turns=10, checkpoints=[10], results_dir=tmp_path,
        composition={"extraction": 1}, distractors=False,
    )
    assert all(e["error"] is None for e in records(bundle, "run_end"))
    (fact,) = json.loads((bundle / "dataset.json").read_text())["0"]["facts"]
    probes = records(bundle, "probe")
    assert {p["backend"] for p in probes} == {"qdrant", "pgvector"}
    for p in probes:
        assert p["fact_id"] == fact["id"]
        assert fact["statements"][0]["text"] in p["context"], p
        assert match_record(p)[0] == "correct", p
