"""The spend budget: computed from recorded tokens, stops cleanly, resumes."""

from __future__ import annotations

import json

import pytest

import run_benchmark as cli
from src.backends.registry import AVAILABLE_BACKENDS
from src.budget import BudgetExceeded, SpendMeter, record_cost, require_prices
from src.bundle import load_manifest
from src.harness import run_benchmark
from src.pricing import price_for
from tests.helpers import records

BUFFER, SUMMARY = AVAILABLE_BACKENDS["buffer"], AVAILABLE_BACKENDS["summary"]
SMALL = dict(num_runs=2, num_turns=10, checkpoints=[5, 10],
             composition={"extraction": 2, "update": 1, "abstention": 1})


def _transcript_cost(bundle) -> float:
    price = price_for("fake-memory-v1")
    return sum(record_cost(price, r) for r in records(bundle))


def test_record_cost_counts_answer_and_memory_write_tokens():
    price = price_for("fake-memory-v1")  # 3 in / 15 out per million
    turn = {"type": "turn", "input_tokens": 1000, "output_tokens": 100,
            "write_input_tokens": 500, "write_output_tokens": 50}
    assert record_cost(price, turn) == pytest.approx((1500 * 3 + 150 * 15) / 1e6)
    assert record_cost(price, {"type": "probe", "input_tokens": 100, "output_tokens": 0}) == pytest.approx(3e-4)
    assert record_cost(price, {"type": "run_end"}) == 0.0


def test_spend_is_recorded_in_the_manifest_even_without_a_budget(tmp_path):
    bundle = run_benchmark([BUFFER], results_dir=tmp_path, **SMALL)
    spend = load_manifest(bundle)["spend"]
    assert spend["budget_usd"] is None and spend["stopped"] is None
    assert spend["answering_usd"] == pytest.approx(_transcript_cost(bundle)) and spend["answering_usd"] > 0
    scores = [json.loads(line) for line in (bundle / "scores.jsonl").read_text().splitlines()]
    judge_cost = price_for("fake-judge-v1").cost(sum(s["judge_input_tokens"] for s in scores),
                                                 sum(s["judge_output_tokens"] for s in scores))
    assert spend["judge_usd"] == pytest.approx(judge_cost) and judge_cost > 0
    assert spend["total_usd"] == pytest.approx(spend["answering_usd"] + spend["judge_usd"])


def test_budget_stops_before_the_next_run_and_the_bundle_resumes(tmp_path):
    with pytest.raises(BudgetExceeded) as stopped:
        run_benchmark([BUFFER, SUMMARY], results_dir=tmp_path, budget_usd=1e-9, **SMALL)
    bundle = stopped.value.bundle
    message = str(stopped.value)
    assert "before buffer run 2 of 2" in message and f"--resume {bundle.name}" in message
    # exactly one (backend, run) ran; nothing was aggregated, so it cannot be published
    assert [(r["backend"], r["run_index"]) for r in records(bundle, "run_end")] == [("buffer", 0)]
    assert not (bundle / "aggregate.json").exists() and not (bundle / "scores.jsonl").exists()
    spend = load_manifest(bundle)["spend"]
    assert spend["stopped"] == "before buffer run 2 of 2" and spend["budget_usd"] == 1e-9
    assert spend["total_usd"] == pytest.approx(_transcript_cost(bundle))

    # the same tiny budget stops a resume at once, without running anything
    with pytest.raises(BudgetExceeded):
        run_benchmark([BUFFER, SUMMARY], results_dir=tmp_path, budget_usd=1e-9, resume=bundle, **SMALL)
    assert len(records(bundle, "run_end")) == 1

    # a higher budget finishes it; the finished run is kept, not rerun
    first_end = records(bundle, "run_end")[0]
    done = run_benchmark([BUFFER, SUMMARY], results_dir=tmp_path, budget_usd=100.0, resume=bundle, **SMALL)
    assert done == bundle and (bundle / "aggregate.json").exists()
    ends = records(bundle, "run_end")
    assert ends[0] == first_end and len(ends) == 4
    spend = load_manifest(bundle)["spend"]
    assert spend["stopped"] is None and spend["budget_usd"] == 100.0
    assert spend["answering_usd"] == pytest.approx(_transcript_cost(bundle))
    assert spend["judge_usd"] > 0

    # same numbers as a run that was never stopped
    straight = run_benchmark([BUFFER, SUMMARY], results_dir=tmp_path / "straight", **SMALL)
    a, b = (json.loads((p / "aggregate.json").read_text())["backends"] for p in (bundle, straight))
    for label in ("buffer", "summary"):
        assert a[label]["recall_overall"] == b[label]["recall_overall"]
        assert a[label]["cost"]["per_conversation_usd"] == pytest.approx(b[label]["cost"]["per_conversation_usd"])


def test_budget_reached_while_judging_keeps_verdicts_and_resumes(tmp_path):
    whole = run_benchmark([BUFFER], results_dir=tmp_path / "whole", **SMALL)
    spend = load_manifest(whole)["spend"]
    # enough for every conversation and some, but not all, of the judging
    limit = spend["answering_usd"] + spend["judge_usd"] / 2
    with pytest.raises(BudgetExceeded, match="while judging") as stopped:
        run_benchmark([BUFFER], results_dir=tmp_path, budget_usd=limit, **SMALL)
    bundle = stopped.value.bundle
    cached = (bundle / "judge_cache.jsonl").read_text().splitlines()
    assert 0 < len(cached) < len(records(bundle, "probe"))
    assert not (bundle / "aggregate.json").exists()
    run_benchmark([BUFFER], results_dir=tmp_path, budget_usd=limit * 10, resume=bundle, **SMALL)
    assert load_manifest(bundle)["spend"]["judge_usd"] == pytest.approx(spend["judge_usd"])
    assert (bundle / "judge_cache.jsonl").read_text().splitlines()[:len(cached)] == cached


def test_spend_of_runs_dropped_on_resume_still_counts(tmp_path):
    with pytest.raises(BudgetExceeded) as stopped:
        run_benchmark([BUFFER], results_dir=tmp_path, budget_usd=1e-9, **SMALL)
    bundle = stopped.value.bundle
    paid = _transcript_cost(bundle)
    # make the finished run look unfinished (as after a kill): it is dropped and rerun on resume
    path = bundle / "transcript.jsonl"
    path.write_text("".join(line + "\n" for line in path.read_text().splitlines()
                            if json.loads(line)["type"] != "run_end"))
    run_benchmark([BUFFER], results_dir=tmp_path, budget_usd=100.0, resume=bundle, **SMALL)
    spend = load_manifest(bundle)["spend"]
    assert spend["dropped_usd"] == pytest.approx(paid)
    assert spend["total_usd"] == pytest.approx(paid + _transcript_cost(bundle) + spend["judge_usd"])


def test_an_unpriced_model_with_a_budget_fails_before_any_work(tmp_path, monkeypatch):
    table = tmp_path / "pricing.yaml"
    table.write_text("models:\n  fake-judge-v1:\n    input_per_mtok: 1\n    output_per_mtok: 1\n"
                     "    source: test\n    checked_on: '2026-01-01'\n")
    monkeypatch.setenv("PRICING_FILE", str(table))
    started = []
    monkeypatch.setattr(BUFFER, "setup", lambda self: started.append(1))
    with pytest.raises(ValueError, match="no price for fake-memory-v1"):
        run_benchmark([BUFFER], results_dir=tmp_path / "out", budget_usd=5.0, **SMALL)
    assert started == [] and not (tmp_path / "out").exists()
    # the judge model must be priced too, unless the judge is off
    table.write_text(table.read_text().replace("fake-judge-v1", "fake-memory-v1"))
    with pytest.raises(ValueError, match="no price for fake-judge-v1"):
        require_prices("fake-memory-v1", "fake-judge-v1")
    assert require_prices("fake-memory-v1", None)[1] is None
    # without a budget an unpriced model still runs, as before
    table.write_text("models: {}\n")
    bundle = run_benchmark([BUFFER], results_dir=tmp_path / "out", **SMALL)
    assert "spend" not in load_manifest(bundle)


@pytest.mark.parametrize("bad", [0, -5.0])
def test_a_budget_must_be_positive(tmp_path, bad):
    with pytest.raises(ValueError, match="positive"):
        run_benchmark([BUFFER], results_dir=tmp_path, budget_usd=bad, **SMALL)


def test_cli_budget_flag_and_env_var_stop_with_exit_code_3(tmp_path, monkeypatch, capsys, fresh_config):
    args = ["--backends", "buffer", "--runs", "2", "--turns", "10", "--checkpoints", "5", "10",
            "--facts", "extraction=2,abstention=1", "--results-dir", str(tmp_path), "--no-viz"]
    assert cli.main(args + ["--budget", "0.000000001"]) == 3
    err = capsys.readouterr().err
    assert "STOPPED ON BUDGET" in err and "--resume" in err
    (bundle,) = (tmp_path / "runs").iterdir()
    assert cli.main(args + ["--budget", "50", "--resume", bundle.name]) == 0
    assert (bundle / "aggregate.json").exists()

    monkeypatch.setenv("BUDGET_USD", "0.000000001")
    fresh_config()
    assert cli.main(args + ["--results-dir", str(tmp_path / "env")]) == 3


def test_meter_without_a_limit_never_stops():
    meter = SpendMeter(price_for("fake-memory-v1"), None)
    meter.add_record({"type": "turn", "input_tokens": 10**9, "output_tokens": 0})
    assert meter.total_usd == pytest.approx(3000.0) and not meter.exceeded()


def test_make_run_v2_is_the_documented_run_and_needs_a_budget():
    """5 runs of 50 turns, a k sweep, the separate priced judge and a budget, in one target."""
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    dry = subprocess.run(["make", "-n", "run-v2", "BUDGET=150"], cwd=root, capture_output=True, text=True)
    command = " ".join(dry.stdout.replace("\\\n", " ").split())
    for part in ("LLM_PROVIDER=do", "JUDGE_PROVIDER=do", "EMBEDDING_PROVIDER=local",
                 "LLM_MODEL=anthropic-claude-4.5-sonnet", "JUDGE_MODEL=openai-gpt-6-sol",
                 "run_benchmark.py --runs 5 --turns 50 --checkpoints 15 25 35 50 --k 2 4 8 --budget 150",
                 "--label v2"):
        assert part in command, part
    assert price_for("openai-gpt-6-sol") is not None  # the budget needs the judge priced
    args = cli.parse_args(command.split("run_benchmark.py", 1)[1].split())
    assert sorted(args.backends) == sorted(AVAILABLE_BACKENDS) and len(args.backends) == 6
    resumed = subprocess.run(["make", "-n", "run-v2", "BUDGET=250", "RESUME=some-run"], cwd=root,
                             capture_output=True, text=True).stdout
    assert "--resume some-run" in resumed and "--label" not in resumed
    assert "make run-v2 BUDGET=150" in (root / "README.md").read_text()
    # without BUDGET the target stops before starting services or the benchmark
    refused = subprocess.run(["make", "run-v2"], cwd=root, capture_output=True, text=True)
    assert refused.returncode != 0 and "needs a spend ceiling" in refused.stdout
