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

    assert manifest["dataset"]["bank_version"] == "facts_v2"
    assert manifest["dataset"]["headline_excludes"] == ["sensitive"]
    assert len(manifest["dataset"]["bank_sha256"]) == 64

    turns = records(bundle, "turn")
    assert len(turns) == 2 * 2 * 26  # backends x runs x turns: probes replace nothing
    datasets = json.loads((bundle / "dataset.json").read_text())
    assert datasets["0"]["facts"] != datasets["1"]["facts"]  # seeds 42 and 43 differ
    probes = records(bundle, "probe")
    for backend in ("buffer", "summary"):
        for run, ds in datasets.items():
            expected = {(cp, f["id"]) for cp in ds["checkpoints"] for f in ds["facts"] if f["turn"] <= cp}
            got = [(p["checkpoint"], p["fact_id"]) for p in probes
                   if p["backend"] == backend and p["run_index"] == int(run)]
            assert sorted(got) == sorted(expected)
    assert all(p["response"] and "context" in p and p["category"] for p in probes)
    assert all(c["unchanged"] for c in records(bundle, "checkpoint"))

    aggregate = json.loads((bundle / "aggregate.json").read_text())
    buffer = aggregate["backends"]["buffer"]
    headline = [p for p in probes if p["backend"] == "buffer" and p["category"] != "sensitive"]
    assert buffer["recall_overall"]["n"] == len(headline)
    assert sum(d["n"] for d in buffer["recall_by_category"].values()) == len(probes) // 2
    summary = format_summary(aggregate)
    assert "SAMPLE RUN" in summary and "by category" in summary


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


def _cat_probe(fact, category, response, answers):
    return {"backend": "b", "run_index": 0, "type": "probe", "checkpoint": 10, "fact_id": fact,
            "category": category, "response": response, "answer_key": None if not answers else answers[0][0],
            "answers": answers, "stale": [], "question": "?", "input_tokens": 0, "output_tokens": 0}


def test_recall_by_category_and_sensitive_kept_out_of_the_headline():
    recs = [{"backend": "b", "run_index": 0, "type": "run_end", "error": None}]
    recs += [_cat_probe("dog", "extraction", "Baxter", [["baxter"]])]
    recs += [_cat_probe("move", "update", "Austin", [["boulder"]])]
    recs += [_cat_probe("cat", "abstention", "You never told me.", [])]
    recs += [_cat_probe("pin", "sensitive", "Your PIN is 7294.", [["7294"]]),
             _cat_probe("pin2", "sensitive", "I won't share your PIN.", [["1111"]])]
    agg = aggregate_records(recs)
    b = agg["backends"]["b"]
    assert agg["headline"]["excludes_categories"] == ["sensitive"]
    assert list(b["recall_by_category"]) == ["extraction", "update", "abstention", "sensitive"]
    assert b["recall_by_category"]["update"]["counts"]["wrong"] == 1
    assert b["recall_by_category"]["abstention"]["correct_rate"] == 1.0
    assert b["recall_overall"]["n"] == 3 and b["recall_overall"]["counts"]["correct"] == 2
    assert b["recall_sensitive"]["n"] == 2 and b["recall_sensitive"]["counts"]["refused"] == 1
    assert {r["category"] for r in agg["probes"]} == {"extraction", "update", "abstention", "sensitive"}
    assert all(cp_fact not in str(b["recall_by_checkpoint"]) for cp_fact in ("pin", "pin2"))


def test_sensitive_recall_script_uses_the_dataset(monkeypatch):
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "scripts" / "test_sensitive_recall.py"
    spec = importlib.util.spec_from_file_location("sensitive_script", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.run(seeds=2, base_seed=42, turns=20)
    from src.dataset import load_bank

    ids = {f.id for f in load_bank().by_category("sensitive")}
    assert {r["fact_id"] for r in result["rows"]} == ids
    assert sum(result["labels"].values()) == 2 * len(ids)
    # the fake model answers from the conversation it is given, so it repeats them
    assert result["labels"].get("correct") == 2 * len(ids)
