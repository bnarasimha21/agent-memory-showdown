"""claude_cli end to end through the vector backends and mem0 on real Qdrant and Postgres."""

import json

import pytest

from src import claude_cli, retry
from src.backends.registry import AVAILABLE_BACKENDS
from src.harness import run_benchmark
from tests.helpers import group, records
from tests.test_claude_cli import fake  # noqa: F401  (fixture)

pytestmark = pytest.mark.integration


def test_buffer_summary_qdrant_mem0_with_the_cli_provider(services, fake, tmp_path):  # noqa: F811
    names = ["buffer", "summary", "qdrant", "mem0"]
    bundle = run_benchmark([AVAILABLE_BACKENDS[n] for n in names], num_runs=1, num_turns=8,
                           checkpoints=[4, 8], results_dir=tmp_path,
                           composition={"extraction": 2, "update": 1})
    ends = {e["backend"]: e for e in records(bundle, "run_end")}
    assert {n: ends[n]["error"] for n in names} == {n: None for n in names}
    turns = group(records(bundle, "turn"), "backend")
    # mem0 pays one extraction call per turn, and the CLI was asked for JSON each time
    assert all(t["write_llm_calls"] == 1 and t["write_input_tokens"] > 0 for t in turns["mem0"])
    json_calls = [c for c in fake.calls() if "single valid JSON object" in c["system"]]
    assert len(json_calls) >= 8
    assert ends["mem0"]["memory_stats"]["size"] > 0 and ends["qdrant"]["memory_stats"]["size"] > 0

    aggregate = json.loads((bundle / "aggregate.json").read_text())
    for n in names:
        assert aggregate["backends"][n]["recall_run_mean"]["mean"] > 0, n
    assert aggregate["pricing"]["model"] == "claude-sonnet-5-5"
    assert all(not c["api_key_visible"] for c in fake.calls())
    manifest = json.loads((bundle / "manifest.json").read_text())
    assert manifest["claude_cli_calls"] == len(fake.calls())
