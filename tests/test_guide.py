"""docs/GUIDE.md is generated from a bundle's aggregate; nothing in it is typed by hand."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from src.site import export, guide
from src.site.data import Bundle, published_bundles


def _rate(rate, n=10):
    return {"n": n, "correct_rate": rate, "correct_ci95": [max(0.0, rate - 0.2), min(1.0, rate + 0.2)]}


def _backend(recall, ci, cost, per_correct, read=1.0, write=2.0, update=0.5, runs=5):
    return {
        "recall_run_mean": {"mean": recall, "ci95": ci, "n": runs, "method": "t"},
        "recall_overall": {"n": 70, "correct_rate": recall, "correct_ci95": [recall - 0.1, min(1.0, recall + 0.1)]},
        "cost": {"per_conversation_usd": cost, "per_conversation_ci95": [cost * 0.9, cost * 1.1],
                 "per_1k_conversations_usd": cost * 1000, "memory_maintenance_per_conversation_usd": 0.0,
                 "per_correct_recall_usd": per_correct},
        "tokens": {"total_tokens": 12345.0},
        "latency": {"retrieve_ms": {"p50": read, "p95": read * 2}, "write_ms": {"p50": write, "p95": write * 2},
                    "llm_ms": {"p50": 4321.0, "p95": 6543.0}},
        "recall_by_category": {"extraction": _rate(1.0), "update": _rate(update), "abstention": _rate(0.25, 4)},
    }


def _bundle(sample=False, **overrides) -> Bundle:
    backends = {
        "buffer": _backend(0.913, [0.82, 0.99], 0.4711, 0.0377, read=0.01, write=0.01, update=0.9),
        "qdrant@k2": _backend(0.701, [0.55, 0.81], 0.0312, 0.0029, read=14.0, write=17.0),
        "qdrant@k8": _backend(0.861, [0.74, 0.97], 0.0623, 0.0048, read=15.0, write=17.0),
        "summary": _backend(0.432, [0.21, 0.66], 0.2222, 0.0366, read=0.02, write=2900.0),
        "mem0@k4": {"error": "All runs failed"},
    }
    backends.update(overrides)
    manifest = {"run_id": "20990101T000000000000Z-guide", "backends": list(backends), "num_runs": 5,
                "num_turns": 50, "checkpoints": [15, 25, 35, 50], "k": [2, 8],
                "llm_provider": "fake" if sample else "do", "llm_model": "anthropic-claude-4.5-sonnet",
                "embedding_provider": "local", "embedding_model": "all-MiniLM-L6-v2", "seeds": [42, 43, 44, 45, 46]}
    aggregate = {
        "run_id": manifest["run_id"], "is_sample": sample,
        "scoring": {"judge_provider": "do", "judge_model": "openai-gpt-6-sol", "judge_is_answering_model": False},
        "pricing": {"model": "anthropic-claude-4.5-sonnet", "input_per_mtok": 3.0, "output_per_mtok": 15.0,
                    "source": "https://example.test/pricing", "checked_on": "2026-10-30"},
        "seeds": {"paired": True, "runs": [0, 1, 2, 3, 4], "dropped": {}},
        "backends": backends,
    }
    return Bundle(Path(guide.REPO_ROOT / "results" / "runs" / manifest["run_id"]), manifest, aggregate)


def test_picks_follow_the_rules():
    p = guide.picks(_bundle())
    assert p["best"] == ["buffer"] and p["separable"]
    # qdrant@k8 [74, 97] overlaps buffer [82, 99]; qdrant@k2 [55, 81] and summary [21, 66] do not
    assert p["contenders"] == ["buffer", "qdrant@k8"] and p["behind"] == ["qdrant@k2", "summary"]
    assert p["cheapest"] == ["qdrant@k8"]                # cheapest of the contenders, not of everything
    assert p["cheapest_per_correct"] == ["qdrant@k2"]    # over all backends
    assert p["fastest"] == ["buffer"]
    assert p["by_category"]["update"]["labels"] == ["buffer"] and p["by_category"]["update"]["rate"] == 0.9
    assert p["by_category"]["extraction"]["all_tied"]
    assert p["k"]["qdrant"]["best_k"] == 8 and p["k"]["qdrant"]["smallest_overlapping_k"] == 2
    assert "mem0@k4" not in p["rows"]  # a failed backend is never picked


def test_guide_shows_recall_cost_latency_and_categories_from_the_aggregate():
    text = guide.render(_bundle())
    assert text.startswith("<!-- GENERATED")
    assert "# Which memory, when, at what cost\n" in text and "SAMPLE" not in text and "(sample)" not in text
    for expected in (
        "| buffer | 91.3% [82, 99] | 5 | 91.3% [81, 100] | 70 |",              # recall with intervals
        "| qdrant@k8 | $0.0623 [$0.0561, $0.0685] | $62.30 | $0.0000 | $0.0048 | 12,345 |",   # cost
        "| summary | 0.0 / 0.0 ms | 2,900 / 5,800 ms | 4,321 / 6,543 ms |",        # memory-layer latency
        "| buffer | 100% [80, 100] (n=10) | 90% [70, 100] (n=10) | 25% [5, 45] (n=4) |",  # by category
        "| mem0@k4 | failed: All runs failed |",
        "**Highest recall:** `buffer` at 91.3% [82, 99].",
        "**Not separated from the best:** `buffer`, `qdrant@k8`.",
        "**Behind the best:** `qdrant@k2`, `summary`",
        "**Pick `qdrant@k8` when you want the cheapest backend whose recall is not separated from the "
        "best:** $0.0623 per conversation at 86.1% [74, 97] recall. The highest-recall backend, `buffer`, "
        "costs $0.4711 per conversation, 7.6 times as much.",
        "**Pick `qdrant@k2` when the unit you pay for is a correct answer:** $0.0029 per correct recall",
        "**Retrieval depth for `qdrant`:** k = 8 had the highest recall (86.1% [74, 97]). k = 2 is the "
        "smallest depth not separated from it (70.1% [55, 81]) at $0.0312 per conversation against $0.0623.",
        "judge `openai-gpt-6-sol`", "$3.00 per million input tokens", "checked 2026-10-30",
        "(../results/runs/20990101T000000000000Z-guide/aggregate.json)",
    ):
        assert expected in text, expected
    assert "—" not in text and "–" not in text


def test_every_figure_moves_with_the_aggregate():
    """Change the aggregate and the guide changes with it: no figure is fixed in the generator."""
    base = _bundle()
    before = guide.render(base)
    changed = copy.deepcopy(base)
    b = changed.aggregate["backends"]
    b["summary"] = _backend(0.987, [0.95, 1.0], 0.0011, 0.0001, read=0.02, write=2900.0)
    after = guide.render(changed)
    assert "**Highest recall:** `summary` at 98.7% [95, 100]." in after
    assert "**Pick `summary` when you want the cheapest backend" in after and "$0.0011 per conversation" in after
    assert "98.7%" not in before and "43.2%" not in after


def test_a_sample_guide_says_so_before_any_number_and_does_not_read_as_advice():
    text = guide.render(_bundle(sample=True))
    lines = text.splitlines()
    assert lines[2] == "# Which memory, when, at what cost (sample data, not a result)"
    assert lines[4] == "> **SAMPLE DATA. THIS IS NOT A BENCHMARK RESULT AND NOT A RECOMMENDATION.**"
    assert text.index("SAMPLE DATA") < text.index("%")  # the warning comes before the first figure
    assert "## Pick this when (rule output on sample data, not advice)" in text
    picks = [line for line in lines if line.startswith("- ") and "**" in line and "Recall** is" not in line
             and "Cost per conversation** covers" not in line and "Memory latency** is" not in line]
    assert picks and all(line.startswith("- (sample) ") for line in picks)


def test_one_run_has_no_intervals_and_the_guide_says_it_cannot_separate_backends():
    single = {label: _backend(r, None, c, c / 10, runs=1)
              for label, r, c in (("buffer", 0.9, 0.5), ("qdrant@k2", 0.8, 0.05), ("qdrant@k8", 0.85, 0.06))}
    bundle = _bundle(**single, summary={"error": "All runs failed"})
    p = guide.picks(bundle)
    assert not p["separable"] and p["contenders"] == ["buffer"] and p["cheapest"] == ["buffer"]
    text = guide.render(bundle)
    assert "One run only, so there are no intervals" in text
    assert "| buffer | 90.0% n/a | 1 |" in text
    assert "with one run there is no interval to compare the other depths against" in text


def test_overlapping_intervals_are_reported_as_not_separated_not_as_a_ranking():
    close = {label: _backend(r, [0.4, 0.95], c, c / 10) for label, r, c in
             (("buffer", 0.8, 0.5), ("qdrant@k2", 0.78, 0.05), ("qdrant@k8", 0.79, 0.06), ("summary", 0.6, 0.2))}
    text = guide.render(_bundle(**close))
    assert "This run does not separate any backend from the best on recall" in text
    assert "Behind the best" not in text
    assert "**Pick `qdrant@k2` when you want the cheapest backend" in text


def test_a_self_judged_real_run_and_an_unpriced_model_are_stated():
    bundle = _bundle()
    bundle.aggregate["scoring"].update(judge_model="anthropic-claude-4.5-sonnet", judge_is_answering_model=True)
    assert "Caveat: the judge was the answering model" in guide.render(bundle)
    unpriced = _bundle()
    unpriced.aggregate["pricing"] = {"model": "some-model", "unpriced": True}
    for data in unpriced.aggregate["backends"].values():
        data.pop("cost", None)
    text = guide.render(unpriced)
    assert "has no entry in `pricing.yaml`, so no cost is shown" in text
    assert "| buffer | n/a | n/a | n/a | n/a | 12,345 |" in text and "cheapest backend" not in text


def test_the_committed_guide_is_generated_from_the_headline_bundle_and_marked_as_a_sample():
    headline = published_bundles()[0]
    committed = guide.GUIDE.read_text(encoding="utf-8")
    assert committed == guide.render(headline) == export.outputs()[guide.GUIDE]
    assert headline.is_sample and "SAMPLE DATA. THIS IS NOT A BENCHMARK RESULT" in committed
    assert "[Which memory, when, at what cost](docs/GUIDE.md)" in export.outputs()[export.README]


def test_export_check_catches_a_hand_edited_guide(tmp_path, monkeypatch):
    target = tmp_path / "GUIDE.md"
    monkeypatch.setattr(guide, "GUIDE", target)
    monkeypatch.setattr(export, "_rel", lambda p: Path(p).name)
    generated = {target: export.outputs()[target]}
    monkeypatch.setattr(export, "outputs", lambda *a, **k: generated)
    target.write_text(generated[target])
    assert export.main(["--check"]) == 0
    target.write_text(generated[target].replace("79.5%", "99.9%"))
    assert export.main(["--check"]) == 1


def test_cli_previews_a_named_bundle_on_stdout_and_writes_only_where_told(tmp_path, capsys):
    headline = published_bundles()[0]
    assert guide.main([str(headline.path)]) == 0
    assert capsys.readouterr().out == guide.render(headline)
    out = tmp_path / "docs" / "preview.md"
    assert guide.main([str(headline.path), "--out", str(out)]) == 0
    assert "SAMPLE, not a result" in capsys.readouterr().out
    assert out.read_text().startswith("<!-- GENERATED") and json.dumps(headline.run_id)[1:-1] in out.read_text()


@pytest.mark.parametrize("label,expected", [("qdrant@k2", ("qdrant", 2)), ("buffer", ("buffer", None)),
                                             ("langgraph_store@k16", ("langgraph_store", 16))])
def test_family_and_k_are_read_from_the_label(label, expected):
    assert guide._family(label) == expected
