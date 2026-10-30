"""The real harness end to end with in-process backends (no docker needed)."""

import json

from run_benchmark import format_summary
from src.aggregate import aggregate_records
from src.backends.registry import AVAILABLE_BACKENDS
from src.harness import run_benchmark
from src.prompts import template_hash
from tests.helpers import records


def test_bundle_has_manifest_transcript_and_aggregate(tmp_path):
    bundle = run_benchmark(
        [AVAILABLE_BACKENDS["buffer"], AVAILABLE_BACKENDS["summary"]],
        num_runs=2, num_turns=26, checkpoints=[12, 25], results_dir=tmp_path,
    )
    manifest = json.loads((bundle / "manifest.json").read_text())
    assert manifest["prompt_hash"] == template_hash()
    assert manifest["llm_provider"] == "fake" and manifest["is_sample"] is True
    assert manifest["seeds"] == [42, 43]
    assert manifest["git"]["sha"]
    assert "langchain-core" in manifest["packages"]

    turns = records(bundle, "turn")
    assert len(turns) == 2 * 2 * 26  # backends x runs x turns: probes replace nothing
    probes = records(bundle, "probe")
    # checkpoint 12: facts at 1,3,7,12 = 4; checkpoint 25: + 18, 25 = 6
    assert len(probes) == 2 * 2 * (4 + 6)
    assert all(p["response"] and "context" in p for p in probes)
    assert {p["fact_id"] for p in probes if p["checkpoint"] == 25} >= {"current_book"}
    assert all(c["unchanged"] for c in records(bundle, "checkpoint"))

    aggregate = json.loads((bundle / "aggregate.json").read_text())
    assert aggregate["backends"]["buffer"]["recall_overall"]["total_probes"] == 20
    assert "SAMPLE RUN" in format_summary(aggregate)


def _probe(cp, fact, response, key="baxter"):
    return {"backend": "b", "run_index": 0, "type": "probe", "checkpoint": cp, "fact_id": fact,
            "response": response, "answer_key": key, "input_tokens": 0, "output_tokens": 0}


def test_overall_recall_is_weighted_by_probe_count():
    recs = [{"backend": "b", "run_index": 0, "type": "run_end", "error": None}]
    recs += [_probe(15, f"f{i}", "Baxter") for i in range(4)]
    recs += [_probe(50, f"f{i}", "Baxter" if i < 5 else "no idea") for i in range(10)]
    agg = aggregate_records(recs)["backends"]["b"]
    assert agg["recall_by_checkpoint"]["15"]["correct_rate"] == 1.0
    assert agg["recall_by_checkpoint"]["50"]["correct_rate"] == 0.5
    # pooled 9/14, not the unweighted mean of checkpoint rates (0.75)
    assert abs(agg["recall_overall"]["correct_rate"] - 9 / 14) < 1e-12
