"""Issue 2: rescore a saved pgvector bundle offline without touching it."""

import hashlib
import json

import pytest

from src.backends.registry import AVAILABLE_BACKENDS
from src.harness import run_benchmark
from src.scoring.judge import Judge
from src.scoring.rescore import main as rescore_main
from src.scoring.rescore import rescore
from src.fakes import FakeMemoryChatModel

pytestmark = pytest.mark.integration


def _tree_digest(path):
    h = hashlib.sha256()
    for f in sorted(p for p in path.rglob("*") if p.is_file()):
        h.update(str(f.relative_to(path)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def test_rescore_reproduces_labels_and_leaves_the_bundle_alone(services, tmp_path):
    bundle = run_benchmark([AVAILABLE_BACKENDS["pgvector"]], num_runs=1, num_turns=10,
                           checkpoints=[5, 10], results_dir=tmp_path)
    original = json.loads((bundle / "aggregate.json").read_text())
    assert original["backends"]["pgvector"]["scorer"] == "judge"
    assert (bundle / "scores.jsonl").exists()
    manifest = json.loads((bundle / "manifest.json").read_text())
    assert manifest["scoring"]["judge_model"] == "fake-judge-v1"
    assert len(manifest["scoring"]["judge_prompt_hash"]) == 64
    before = _tree_digest(bundle)

    out, rescored = rescore(bundle, tmp_path / "rescored",
                            judge=Judge(FakeMemoryChatModel(), "fake", "fake-judge-v1"))
    assert _tree_digest(bundle) == before
    for key in ("recall_overall",):
        assert (rescored["backends"]["pgvector"][key]["counts"]
                == original["backends"]["pgvector"][key]["counts"])
    assert (rescored["backends"]["pgvector"]["matcher"]["recall_overall"]["counts"]
            == original["backends"]["pgvector"]["matcher"]["recall_overall"]["counts"])
    assert rescored["agreement"]["kappa"] == 1.0 or rescored["agreement"]["observed"] == 1.0
    assert (out / "scores.jsonl").exists() and (out / "aggregate.json").exists()
    probes = rescored["probes"]
    assert probes and all(p["judge_label"] and p["judge_rationale"] for p in probes)

    # the CLI path, matcher only, refuses to write inside the bundle
    assert rescore_main([str(bundle), "--out", str(tmp_path / "cli"), "--no-judge"]) == 0
    with pytest.raises(ValueError):
        rescore(bundle, bundle / "inside", use_judge=False)
    assert _tree_digest(bundle) == before
