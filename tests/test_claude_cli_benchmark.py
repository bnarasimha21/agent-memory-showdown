"""A short benchmark end to end with LLM_PROVIDER=claude_cli, and resuming an interrupted one.

Buffer and summary need no services, so these run in `make test-unit`.
The service-backed backends are in tests/integration/test_claude_cli_services.py.
"""

from __future__ import annotations

import json

import pytest

from src import claude_cli, retry
from src.backends.registry import AVAILABLE_BACKENDS
from src.harness import run_benchmark
from tests.fake_claude import install
from tests.helpers import records
from tests.test_claude_cli import fake, sleeps  # noqa: F401  (fixtures)

COMPOSITION = {"extraction": 1, "update": 1}
BACKENDS = [AVAILABLE_BACKENDS["buffer"], AVAILABLE_BACKENDS["summary"]]


def bench(tmp_path, **kw):
    return run_benchmark(BACKENDS, num_runs=2, num_turns=6, checkpoints=[3, 6], results_dir=tmp_path,
                         composition=COMPOSITION, **kw)


def test_short_benchmark_records_model_tokens_cost_and_caveats(fake, tmp_path):
    bundle = bench(tmp_path)
    manifest = json.loads((bundle / "manifest.json").read_text())
    assert manifest["llm_provider"] == "claude_cli" and manifest["llm_model"] == "claude-sonnet-5-5"
    # (is_sample is true here only because conftest forces fake embeddings)
    assert manifest["llm_provider"] != "fake" and manifest["judge_provider"] == "claude_cli"
    assert manifest["provider_caveats"]["llm_latency_comparable"] is False
    assert manifest["provider_caveats"]["temperature_controllable"] is False
    assert manifest["claude_cli_calls"] == len(fake.calls())

    scoring = json.loads((bundle / "scoring.json").read_text())
    assert scoring["judge_provider"] == "claude_cli" and scoring["judge_model"] == "claude-sonnet-5-5"
    assert scoring["judge_is_answering_model"] is True

    turns = records(bundle, "turn")
    assert len(turns) == 2 * 2 * 6
    assert all(t["input_tokens"] > 0 and t["output_tokens"] > 0 for t in turns)
    summary_turns = [t for t in turns if t["backend"] == "summary"]
    assert all(t["write_llm_calls"] == 1 and t["write_input_tokens"] > 0 for t in summary_turns)
    assert not any(t["write_llm_calls"] for t in turns if t["backend"] == "buffer")

    aggregate = json.loads((bundle / "aggregate.json").read_text())
    assert aggregate["provider_caveats"]["cost_basis"] == "api_equivalent"
    assert aggregate["pricing"]["model"] == "claude-sonnet-5-5" and "unpriced" not in aggregate["pricing"]
    for name in ("buffer", "summary"):
        data = aggregate["backends"][name]
        assert data["recall_run_mean"]["mean"] > 0
        assert data["cost"]["per_1k_conversations_usd"] > 0
    assert all(not c["api_key_visible"] for c in fake.calls())


def test_usage_limit_in_the_middle_of_a_run_pauses_and_loses_nothing(fake, tmp_path, sleeps):
    fake.plan("ok", "ok", "ok", {"limit": "You've hit your limit"}, "ok")
    bundle = bench(tmp_path)
    ends = records(bundle, "run_end")
    assert all(e["error"] is None for e in ends) and len(ends) == 4
    manifest = json.loads((bundle / "manifest.json").read_text())
    assert [p["seconds"] for p in manifest["usage_limit_pauses"]] == [1800.0]
    assert sleeps == [1800.0]
    probes = records(bundle, "probe")
    paused = [r for r in records(bundle, "turn") + probes
              if r["llm_retry_wait_ms"] or r.get("write_retry_wait_ms")]
    assert len(paused) <= 1  # the pause fell on one call and is reported as wait, not latency
    for r in paused:
        assert r["llm_ms"] < 1800 * 1000 and r.get("write_ms", 0) < 1800 * 1000
    assert sum(1 for t in records(bundle, "turn") if t["llm_retries"] or t["write_retries"]) <= 1


def test_interrupted_benchmark_resumes_without_repeating_finished_work(fake, tmp_path, sleeps, monkeypatch):
    # Calls 12 to 39 fail permanently: some runs die half way, the rest finish.
    fake.rules(fail_from=12, fail_until=40)
    first = bench(tmp_path)
    ends = records(first, "run_end")
    failed = {(e["backend"], e["run_index"]) for e in ends if e["error"]}
    assert failed and len(failed) < len(ends)

    fake.rules()  # the outage is over
    again = bench(tmp_path, resume=first)
    assert again == first

    ends = records(first, "run_end")
    assert sorted((e["backend"], e["run_index"]) for e in ends) == [
        (b, i) for b in ("buffer", "summary") for i in (0, 1)]  # exactly one end per run, none duplicated
    assert all(e["error"] is None for e in ends)
    turns = records(first, "turn")
    assert len(turns) == 24 and len({(t["backend"], t["run_index"], t["turn"]) for t in turns}) == 24
    manifest = json.loads((first / "manifest.json").read_text())
    assert len(manifest["resumed_at"]) == 1
    assert manifest["claude_cli_calls"] == len(fake.calls())

    aggregate = json.loads((first / "aggregate.json").read_text())
    assert aggregate["backends"]["buffer"]["recall_run_mean"]["n"] == 2

    # Resuming a finished bundle does no model work at all: judge verdicts come from the cache.
    done_calls = len(fake.calls())
    bench(tmp_path, resume=first)
    assert len(fake.calls()) == done_calls
    cached = (first / "judge_cache.jsonl").read_text().splitlines()
    assert len(cached) == len(records(first, "probe"))


def test_resume_refuses_a_different_configuration(fake, tmp_path):
    bundle = bench(tmp_path)
    with pytest.raises(ValueError, match="num_turns"):
        run_benchmark(BACKENDS, num_runs=2, num_turns=8, checkpoints=[3, 6], results_dir=tmp_path,
                      composition=COMPOSITION, resume=bundle.name)


def test_resume_by_bare_run_id_finds_the_bundle(fake, tmp_path):
    bundle = bench(tmp_path)
    assert bench(tmp_path, resume=bundle.name) == bundle


def test_a_missing_embedding_model_stops_the_run_before_any_paid_call(fake, tmp_path, monkeypatch):
    import src.llm_factory as factory

    def broken():
        raise ImportError("Could not import sentence_transformers")

    monkeypatch.setattr(factory, "get_embeddings", broken)
    with pytest.raises(RuntimeError, match="embedding model.*cannot be loaded"):
        run_benchmark([AVAILABLE_BACKENDS["buffer"], AVAILABLE_BACKENDS["qdrant"]], num_runs=2,
                      num_turns=6, checkpoints=[3, 6], results_dir=tmp_path, composition=COMPOSITION)
    assert fake.calls() == []
    # Backends that need no embeddings do not load the model at all.
    bench(tmp_path, judge=False)
