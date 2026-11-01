"""Issue 4: one fact from each category through all four backends on real services."""

import json
from collections import Counter

import pytest

from src.backends.registry import AVAILABLE_BACKENDS
from src.dataset import CATEGORIES
from src.harness import run_benchmark
from tests.helpers import records

pytestmark = pytest.mark.integration

BACKENDS = ["buffer", "summary", "qdrant", "pgvector"]


def test_every_category_is_reported_with_the_expected_probe_count(services, tmp_path):
    bundle = run_benchmark(
        [AVAILABLE_BACKENDS[b] for b in BACKENDS], num_runs=2, num_turns=30,
        checkpoints=[15, 30], results_dir=tmp_path, composition={c: 1 for c in CATEGORIES},
    )
    assert all(e["error"] is None for e in records(bundle, "run_end"))
    datasets = json.loads((bundle / "dataset.json").read_text())
    assert len(datasets) == 2

    expected: Counter = Counter()
    for ds in datasets.values():
        assert sorted(f["category"] for f in ds["facts"]) == sorted(CATEGORIES)
        for cp in ds["checkpoints"]:
            expected.update(f["category"] for f in ds["facts"] if f["turn"] <= cp)
    # the two seeds realize different facts
    assert ([f["values"] for f in datasets["0"]["facts"]]
            != [f["values"] for f in datasets["1"]["facts"]])

    agg = json.loads((bundle / "aggregate.json").read_text())
    for backend in BACKENDS:
        b = agg["backends"][backend]
        assert "error" not in b, b
        by_cat = b["recall_by_category"]
        assert set(by_cat) == set(CATEGORIES)
        assert {c: by_cat[c]["n"] for c in CATEGORIES} == dict(expected), backend
        # abstention and sensitive are reported on their own and left out of the headline
        assert b["recall_sensitive"]["n"] == expected["sensitive"]
        assert b["recall_abstention"]["n"] == expected["abstention"]
        assert b["recall_overall"]["n"] == (sum(expected.values()) - expected["sensitive"]
                                            - expected["abstention"])
        assert sum(e["n"] for e in b["recall_by_checkpoint"].values()) == b["recall_overall"]["n"]

    probes = records(bundle, "probe")
    abstention = [p for p in probes if p["category"] == "abstention"]
    assert len(abstention) == len(BACKENDS) * expected["abstention"]
    for p in abstention:
        assert p["answer_key"] is None and p["answers"] == [] and p["planted_at"] is None
    scores = [json.loads(line) for line in (bundle / "scores.jsonl").read_text().splitlines()]
    abst_scores = [s for s in scores if s["fact_id"] in {p["fact_id"] for p in abstention}]
    assert abst_scores
    for s in abst_scores:
        assert s["matcher_label"] in ("correct", "wrong", "refused")
        assert "never stated" in s["matcher_reason"]
        assert s["judge_label"] in ("correct", "wrong", "refused")

    update = [p for p in probes if p["category"] == "update"]
    assert update and all(p["stale"] for p in update)
