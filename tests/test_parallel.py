"""PARALLEL > 1 runs conversations and judge calls at once and must not change the results."""

import json

from src.backends.registry import AVAILABLE_BACKENDS
from src.config import config
from src.harness import run_benchmark


def _recall(bundle):
    agg = json.loads((bundle / "aggregate.json").read_text())
    return {name: (b["num_valid_runs"], b["recall_run_mean"]["mean"]) for name, b in agg["backends"].items()}


def _run(tmp_path, monkeypatch, parallel):
    monkeypatch.setattr(config, "PARALLEL", parallel)
    return run_benchmark([AVAILABLE_BACKENDS["buffer"], AVAILABLE_BACKENDS["summary"]], num_runs=3,
                         num_turns=20, checkpoints=[10, 20], results_dir=tmp_path / str(parallel),
                         composition={"extraction": 2, "update": 1, "abstention": 1})


def test_a_parallel_run_gives_the_same_recall_as_a_sequential_one(tmp_path, monkeypatch):
    sequential = _run(tmp_path, monkeypatch, 1)
    parallel = _run(tmp_path, monkeypatch, 6)
    assert _recall(parallel) == _recall(sequential)
    assert all(valid == 3 for valid, _ in _recall(parallel).values())


def test_the_manifest_says_when_a_run_was_parallel(tmp_path, monkeypatch):
    manifest = json.loads((_run(tmp_path, monkeypatch, 4) / "manifest.json").read_text())
    assert manifest["parallel"] == 4
    assert "not comparable" in manifest["provider_caveats"]["parallel_note"]
    manifest = json.loads((_run(tmp_path, monkeypatch, 1) / "manifest.json").read_text())
    assert manifest["parallel"] == 1 and "parallel_note" not in manifest["provider_caveats"]
