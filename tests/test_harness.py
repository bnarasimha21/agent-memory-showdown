"""The real harness end to end with in-process backends (no docker needed)."""

import json

import pytest

from run_benchmark import format_summary
from src.aggregate import aggregate_records, wilson
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
    assert manifest["dataset"]["headline_excludes"] == ["abstention", "sensitive"]
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
    headline = [p for p in probes if p["backend"] == "buffer"
                and p["category"] not in ("abstention", "sensitive")]
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


def test_recall_by_category_with_abstention_and_sensitive_kept_out_of_the_headline():
    recs = [{"backend": "b", "run_index": 0, "type": "run_end", "error": None}]
    recs += [_cat_probe("dog", "extraction", "Baxter", [["baxter"]])]
    recs += [_cat_probe("move", "update", "Austin", [["boulder"]])]
    recs += [_cat_probe("cat", "abstention", "You never told me.", [])]
    recs += [_cat_probe("pin", "sensitive", "Your PIN is 7294.", [["7294"]]),
             _cat_probe("pin2", "sensitive", "I won't share your PIN.", [["1111"]])]
    agg = aggregate_records(recs)
    b = agg["backends"]["b"]
    assert agg["headline"]["excludes_categories"] == ["abstention", "sensitive"]
    assert list(b["recall_by_category"]) == ["extraction", "update", "abstention", "sensitive"]
    assert b["recall_by_category"]["update"]["counts"]["wrong"] == 1
    assert b["recall_by_category"]["abstention"]["correct_rate"] == 1.0
    assert b["recall_overall"]["n"] == 2 and b["recall_overall"]["counts"]["correct"] == 1
    assert b["recall_abstention"]["n"] == 1 and b["recall_abstention"]["correct_rate"] == 1.0
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


@pytest.mark.parametrize("llm,judge,emb,sample", [
    ("fake", "fake", "fake", True),
    ("do", "do", "fake", True),      # real chat model, fake embeddings: still a sample
    ("do", "fake", "local", True),   # fake judge labels: a sample
    ("do", "do", "local", False),
])
def test_any_fake_provider_marks_the_run_as_a_sample(monkeypatch, fresh_config, llm, judge, emb, sample):
    from src.harness import build_manifest, is_sample_config

    monkeypatch.setenv("LLM_PROVIDER", llm)
    monkeypatch.setenv("JUDGE_PROVIDER", judge)
    monkeypatch.setenv("EMBEDDING_PROVIDER", emb)
    fresh_config()
    assert is_sample_config() is sample
    assert build_manifest(["buffer"], 1, 10, {}, [10], 4)["is_sample"] is sample


@pytest.mark.parametrize("label", ["a b", "x#y", "what?", "a/b", "*/", "..", "-lead", "x" * 65])
def test_run_labels_that_would_break_a_path_or_url_are_rejected(label):
    from run_benchmark import parse_args
    from src.bundle import new_run_id

    with pytest.raises(ValueError):
        new_run_id(label)
    with pytest.raises(SystemExit):
        parse_args(["--label", label])


def test_good_labels_make_valid_run_ids():
    from run_benchmark import parse_args
    from src.bundle import new_run_id, validate_run_id

    assert parse_args(["--label", "sample-fake_2.1"]).label == "sample-fake_2.1"
    run_id = new_run_id("sample-fake_2.1")
    assert validate_run_id(run_id) == run_id and run_id.endswith("-sample-fake_2.1")
    for bad in ("../x", "a/b", "a b", "x..y"):
        with pytest.raises(ValueError):
            validate_run_id(bad)


def test_a_backend_that_remembers_nothing_scores_zero_headline_recall(tmp_path):
    """Abstention facts are probed at every checkpoint; in the headline they let a
    backend that stores nothing and always says "you never told me" score ~35%."""
    from langchain_core.language_models.fake_chat_models import FakeListChatModel

    from src.backends.base import WriteStats
    from src.backends.buffer_memory import BufferMemoryBackend

    class NullBackend(BufferMemoryBackend):
        name = "null"

        def __init__(self, **kwargs):
            kwargs["llm"] = FakeListChatModel(responses=["I'm sorry, you never told me that."])
            super().__init__(**kwargs)

        def write(self, human_message, ai_message):
            return WriteStats()  # stores nothing

    bundle = run_benchmark([NullBackend], num_runs=2, num_turns=20, checkpoints=[10, 20],
                           results_dir=tmp_path, judge=False,
                           composition={"extraction": 2, "update": 1, "temporal": 1, "multi_hop": 1,
                                        "abstention": 1, "sensitive": 1})
    null = json.loads((bundle / "aggregate.json").read_text())["backends"]["null"]
    assert null["recall_overall"]["n"] > 0
    assert null["recall_overall"]["correct_rate"] == 0.0
    assert null["recall_run_mean"]["mean"] == 0.0
    assert null["recall_abstention"]["correct_rate"] == 1.0  # reported, just not in the headline


def _end(backend, run, error=None):
    return {"backend": backend, "run_index": run, "type": "run_end", "error": error}


def _run_probe(backend, run, fact, response):
    return dict(_probe(10, fact, response), backend=backend, run_index=run)


def test_backends_are_compared_on_runs_valid_for_all_of_them(caplog):
    # b fails run 1, which happens to be the run a does worst on: comparing a's
    # runs 0 and 1 with b's run 0 alone would flatter b by a different dataset.
    recs = [_end("a", 0), _end("a", 1), _end("b", 0), _end("b", 1, error="RateLimitError")]
    recs += [_run_probe("a", 0, "f", "Baxter"), _run_probe("a", 1, "f", "no idea")]
    recs += [_run_probe("b", 0, "f", "Baxter"), _run_probe("b", 1, "f", "no idea")]
    with caplog.at_level("WARNING", logger="src.aggregate"):
        agg = aggregate_records(recs)
    assert agg["seeds"] == {"paired": True, "runs": [0], "dropped": {"a": [1]}}
    a, b = agg["backends"]["a"], agg["backends"]["b"]
    assert a["runs_used"] == b["runs_used"] == [0]
    assert a["num_valid_runs"] == 2 and b["num_valid_runs"] == 1
    assert a["recall_overall"]["n"] == 1 and a["recall_run_mean"]["mean"] == 1.0
    assert "PAIRED SEEDS" in caplog.text
    assert "WARNING: backends compared on paired runs [0] only" in format_summary(agg)


def test_no_common_run_falls_back_to_each_backends_own_runs_and_says_so(caplog):
    recs = [_end("a", 0), _end("a", 1, error="x"), _end("b", 0, error="x"), _end("b", 1)]
    recs += [_run_probe("a", 0, "f", "Baxter"), _run_probe("b", 1, "f", "Baxter")]
    with caplog.at_level("WARNING", logger="src.aggregate"):
        agg = aggregate_records(recs)
    assert agg["seeds"]["paired"] is False and agg["seeds"]["runs"] is None
    assert agg["backends"]["a"]["runs_used"] == [0] and agg["backends"]["b"]["runs_used"] == [1]
    assert "UNPAIRED" in caplog.text and "not compared on the same datasets" in format_summary(agg)


def test_a_backend_that_failed_every_run_does_not_unpair_the_others():
    recs = [_end("a", 0), _end("a", 1), _end("b", 0), _end("b", 1), _end("c", 0, "x"), _end("c", 1, "x")]
    recs += [_run_probe(x, r, "f", "Baxter") for x in "ab" for r in (0, 1)]
    agg = aggregate_records(recs)
    assert agg["seeds"] == {"paired": True, "runs": [0, 1], "dropped": {}}
    assert agg["backends"]["c"]["error"] == "All runs failed"


def test_run_mean_uses_a_t_interval_and_one_run_has_none():
    recs = [_end("a", i) for i in range(3)]
    recs += [_run_probe("a", 0, f"f{j}", "Baxter") for j in range(4)]
    recs += [_run_probe("a", 1, f"f{j}", "Baxter" if j < 2 else "no") for j in range(4)]
    recs += [_run_probe("a", 2, f"f{j}", "Baxter" if j < 3 else "no") for j in range(4)]
    rm = aggregate_records(recs)["backends"]["a"]["recall_run_mean"]
    assert rm["method"] == "t" and rm["n"] == 3 and rm["mean"] == pytest.approx(0.75)
    # sd of (1, .5, .75) is .25; t(2) = 4.303: half width .621, clipped to [0, 1]
    assert rm["ci95"] == pytest.approx([0.75 - 4.303 * 0.25 / 3 ** 0.5, 1.0])
    lo, hi = rm["bootstrap_ci95"]
    assert rm["ci95"][0] < lo  # the bootstrap over three runs is the narrower one
    single = aggregate_records([_end("a", 0), _run_probe("a", 0, "f", "Baxter")])
    one = single["backends"]["a"]["recall_run_mean"]
    assert one["ci95"] is None and one["n"] == 1
    assert "[no interval]" in format_summary(single)


def test_identical_runs_fall_back_to_a_pooled_wilson_interval():
    # Both runs score 1 of 2: the t interval would be [0.5, 0.5], claiming a
    # certainty two runs of two probes cannot support.
    recs = [_end("a", 0), _end("a", 1)]
    recs += [_run_probe("a", r, f"f{j}", "Baxter" if j == 0 else "no") for r in (0, 1) for j in (0, 1)]
    agg = aggregate_records(recs)
    rm = agg["backends"]["a"]["recall_run_mean"]
    assert rm["mean"] == 0.5 and rm["method"] == "wilson-pooled" and rm["degenerate_t"] is True
    assert rm["ci95"] == pytest.approx(wilson(2, 4))
    assert rm["ci95"][1] - rm["ci95"][0] > 0.4
    assert "(runs identical: pooled Wilson)" in format_summary(agg)


def test_a_run_whose_judge_calls_all_failed_is_scored_by_the_matcher():
    recs = [_end("a", 0), _run_probe("a", 0, "f", "Baxter")]
    scores = [{"backend": "a", "run_index": 0, "checkpoint": 10, "fact_id": "f",
               "matcher_label": "correct", "judge_label": "error", "judge_rationale": "429"}]
    b = aggregate_records(recs, scores=scores)["backends"]["a"]
    assert b["scorer"] == "matcher" and b["judge"]["errors"] == 1


@pytest.mark.parametrize("kwargs", [{"num_runs": 0}, {"num_turns": 0}, {"num_runs": -1}])
def test_zero_runs_or_turns_is_an_error_not_the_default(tmp_path, kwargs):
    with pytest.raises(ValueError, match="at least 1"):
        run_benchmark([AVAILABLE_BACKENDS["buffer"]], results_dir=tmp_path, judge=False,
                      **{"num_runs": 1, "num_turns": 10, **kwargs})
    assert not (tmp_path / "runs").exists()


def test_a_run_with_no_headline_probes_fails_before_any_work(tmp_path):
    with pytest.raises(ValueError, match="no headline probe"):
        run_benchmark([AVAILABLE_BACKENDS["buffer"]], num_runs=1, num_turns=10, checkpoints=[10],
                      composition={"abstention": 1, "sensitive": 1}, results_dir=tmp_path, judge=False)
    assert not (tmp_path / "runs").exists()


def test_the_judge_is_resolved_before_any_conversation(tmp_path, monkeypatch):
    import src.scoring.judge as judge_mod

    def broken():
        raise RuntimeError("JUDGE_MODEL is not a model")

    monkeypatch.setattr(judge_mod, "get_judge", broken)
    started = []
    monkeypatch.setattr(AVAILABLE_BACKENDS["buffer"], "setup", lambda self: started.append(1))
    with pytest.raises(RuntimeError, match="not a model"):
        run_benchmark([AVAILABLE_BACKENDS["buffer"]], num_runs=1, num_turns=10, checkpoints=[10],
                      composition={"extraction": 1}, results_dir=tmp_path, judge=True)
    assert started == [] and not (tmp_path / "runs").exists()


def test_manifest_k_reflects_what_ran(tmp_path):
    from src.backends.registry import AVAILABLE_BACKENDS as B

    def manifest(classes, ks):
        bundle = run_benchmark(classes, num_runs=1, num_turns=10, checkpoints=[10],
                               composition={"extraction": 1},
                               results_dir=tmp_path, judge=False, ks=ks)
        return json.loads((bundle / "manifest.json").read_text())

    class TopK(B["buffer"]):
        name = "topk"
        uses_k = True

    only_buffer = manifest([B["buffer"]], [2, 4])
    assert only_buffer["k"] is None and only_buffer["backends"] == ["buffer"]
    swept = manifest([B["buffer"], TopK], [2, 4])
    assert swept["k"] == [2, 4] and swept["backends"] == ["buffer", "topk@k2", "topk@k4"]
    single = manifest([TopK], [3])
    assert single["k"] == 3 and single["backends"] == ["topk"]


def test_matplotlib_charts_are_not_overwritten_by_plotly_pngs(tmp_path, monkeypatch):
    import plotly.graph_objects as go

    from src import visualize

    bundle = run_benchmark([AVAILABLE_BACKENDS["buffer"]], num_runs=1, num_turns=10, checkpoints=[10],
                           composition={"extraction": 1}, results_dir=tmp_path, judge=False)
    written = []
    monkeypatch.setattr(go.Figure, "write_image", lambda self, path, *a, **k: written.append(path))
    out = tmp_path / "charts"
    visualize.generate_all(bundle / "aggregate.json", out)
    assert [p for p in written if not p.endswith("cost_vs_recall.png")] == []
    assert (out / "memory_decay_curve.png").exists() and (out / "memory_decay_curve.html").exists()


def test_docker_image_leaves_out_secrets_and_compose_passes_judge_settings():
    from pathlib import Path

    import yaml

    root = Path(__file__).resolve().parents[1]
    ignored = (root / ".dockerignore").read_text().splitlines()
    assert ".env" in ignored and "!.env.example" in ignored
    env = yaml.safe_load((root / "docker-compose.yml").read_text())["services"]["benchmark"]["environment"]
    names = {e.split("=", 1)[0] for e in env}
    assert {"JUDGE_PROVIDER", "JUDGE_MODEL", "JUDGE", "DO_INFERENCE_URL", "LLM_MAX_RETRIES"} <= names


def test_a_fake_judge_provider_does_not_make_a_no_judge_run_a_sample(monkeypatch, fresh_config):
    from src.harness import build_manifest, is_sample_config

    monkeypatch.setenv("LLM_PROVIDER", "do")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local")
    monkeypatch.setenv("JUDGE_PROVIDER", "fake")
    fresh_config()
    assert is_sample_config(judge=False) is False
    assert build_manifest(["buffer"], 1, 10, {}, [10], 4, judge=False)["is_sample"] is False
    assert build_manifest(["buffer"], 1, 10, {}, [10], 4, judge=True)["is_sample"] is True


def _real_manifest(**extra):
    return {"run_id": "r", "llm_provider": "do", "embedding_provider": "local",
            "llm_model": "anthropic-claude-4.5-sonnet", "is_sample": False, **extra}


def test_aggregate_sample_flag_follows_the_scoring_in_effect():
    recs = [_end("a", 0), _run_probe("a", 0, "f", "Baxter")]
    fake = {"judge_provider": "fake", "judge_model": "fake-judge-v1"}
    real = {"judge_provider": "do", "judge_model": "some-judge"}
    assert aggregate_records(recs, _real_manifest(), scoring={"judge_provider": None})["is_sample"] is False
    assert aggregate_records(recs, _real_manifest(), scoring=fake)["is_sample"] is True
    assert aggregate_records(recs, _real_manifest(), scoring=real)["is_sample"] is False
    # A fake chat model or embedder is a sample whatever the judge.
    assert aggregate_records(recs, _real_manifest(llm_provider="fake"), scoring=real)["is_sample"] is True
    # Manifests without providers keep their own flag.
    assert aggregate_records(recs, {"is_sample": True})["is_sample"] is True


def test_rescoring_a_real_bundle_with_a_fake_judge_is_marked_a_sample(tmp_path):
    from src.fakes import FakeMemoryChatModel
    from src.scoring.judge import Judge
    from src.scoring.rescore import rescore

    bundle = run_benchmark([AVAILABLE_BACKENDS["buffer"]], num_runs=1, num_turns=10, checkpoints=[10],
                           composition={"extraction": 1}, results_dir=tmp_path / "res", judge=False)
    # Pretend the conversations came from real providers.
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest.update(llm_provider="do", embedding_provider="local", is_sample=False)
    (bundle / "manifest.json").write_text(json.dumps(manifest))
    out, agg = rescore(bundle, tmp_path / "rescored",
                       judge=Judge(FakeMemoryChatModel(), "fake", "fake-judge-v1"))
    assert agg["is_sample"] is True
    assert json.loads((out / "aggregate.json").read_text())["is_sample"] is True
    _, agg = rescore(bundle, tmp_path / "matcher-only", use_judge=False)
    assert agg["is_sample"] is False
