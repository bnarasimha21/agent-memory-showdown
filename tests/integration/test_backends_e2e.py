"""Issue 5: every registered backend runs end to end on real services and cleans up after itself."""

import json

import psycopg
import pytest
from qdrant_client import QdrantClient

from run_benchmark import main as cli_main
from src.backends.langgraph_store_memory import NAMESPACE_ROOT
from src.backends.mem0_memory import COLLECTION_PREFIX as MEM0_PREFIX
from src.backends.pgvector_memory import COLLECTION_PREFIX as PG_PREFIX
from src.backends.qdrant_memory import COLLECTION_PREFIX as QDRANT_PREFIX
from src.backends.registry import AVAILABLE_BACKENDS
from src.harness import run_benchmark
from tests.helpers import group, records

pytestmark = pytest.mark.integration

ALL = list(AVAILABLE_BACKENDS)
# Backends whose write step calls the LLM (summary rewrites, mem0 extracts).
LLM_WRITERS = {"summary", "mem0"}


def _leftovers(config, session_ids: dict[str, str]) -> dict[str, list]:
    """Anything a backend's teardown should have removed, per backend."""
    client = QdrantClient(url=config.QDRANT_URL)
    try:
        collections = {c.name for c in client.get_collections().collections}
    finally:
        client.close()
    with psycopg.connect(config.postgres_dsn) as conn:
        pg = conn.execute(
            "SELECT name FROM langchain_pg_collection WHERE name = %s",
            (f"{PG_PREFIX}{session_ids['pgvector'][:8]}",),
        ).fetchall()
        store = conn.execute(
            "SELECT key FROM store WHERE prefix = %s",
            (f"{NAMESPACE_ROOT}.{session_ids['langgraph_store']}",),
        ).fetchall()
    q = f"{QDRANT_PREFIX}{session_ids['qdrant'][:8]}"
    m = f"{MEM0_PREFIX}{session_ids['mem0'][:8]}"
    return {
        "qdrant": [c for c in collections if c == q],
        "mem0": [c for c in collections if c in (m, f"{m}_entities")],
        "pgvector": pg,
        "langgraph_store": store,
    }


def test_every_backend_writes_retrieves_and_tears_down(services, tmp_path):
    bundle = run_benchmark(
        [AVAILABLE_BACKENDS[b] for b in ALL],
        num_runs=1, num_turns=15, checkpoints=[15], results_dir=tmp_path,
        composition={"extraction": 1, "update": 1}, judge=False,
    )
    manifest = json.loads((bundle / "manifest.json").read_text())
    assert manifest["backends"] == ALL

    ends = {e["backend"]: e for e in records(bundle, "run_end")}
    assert {b: e["error"] for b, e in ends.items()} == {b: None for b in ALL}
    assert all(e["teardown_error"] is None for e in ends.values())
    assert all(ends[b]["memory_stats"]["size"] > 0 for b in ALL)

    # Writes: every turn reaches memory; only the LLM-writing backends pay LLM calls for it.
    turns = group(records(bundle, "turn"), "backend")
    for b in ALL:
        assert len(turns[b]) == 15
        calls = [t["write_llm_calls"] for t in turns[b]]
        if b in LLM_WRITERS:
            assert all(c == 1 for c in calls), (b, calls)
            assert all(t["write_input_tokens"] > 0 for t in turns[b]), b
        else:
            assert not any(calls), (b, calls)

    # Retrieval: the planted extraction fact reaches the prompt context of every backend.
    ds = json.loads((bundle / "dataset.json").read_text())["0"]
    facts = {f["category"]: f for f in ds["facts"]}
    planted = facts["extraction"]["statements"][0]["text"]
    probes = group(records(bundle, "probe"), "backend", "category")
    for b in ALL:
        (p,) = probes[(b, "extraction")]
        assert planted in p["context"], (b, p["context"])
        assert p["write_llm_calls"] == 0
    assert len(facts["update"]["statements"]) == 2

    # Probe isolation held at the checkpoint for every backend.
    for cp in records(bundle, "checkpoint"):
        assert cp["unchanged"], cp

    session_ids = {s["backend"]: s["session_id"] for s in records(bundle, "run_start")}
    assert _leftovers(services, session_ids) == {
        "qdrant": [], "mem0": [], "pgvector": [], "langgraph_store": []
    }


def test_k_sweep_from_the_cli_labels_each_depth(services, tmp_path):
    rc = cli_main([
        "--backends", "qdrant", "buffer", "--runs", "1", "--turns", "8", "--checkpoints", "8",
        "--facts", "extraction=1", "--no-distractors", "--no-judge", "--no-viz",
        "--k", "1", "3", "--results-dir", str(tmp_path),
    ])
    assert rc == 0
    (bundle,) = (tmp_path / "runs").iterdir()
    manifest = json.loads((bundle / "manifest.json").read_text())
    assert manifest["backends"] == ["qdrant@k1", "qdrant@k3", "buffer"]
    assert manifest["k"] == [1, 3]
    starts = {s["backend"]: s["k"] for s in records(bundle, "run_start")}
    assert starts == {"qdrant@k1": 1, "qdrant@k3": 3, "buffer": services.RETRIEVAL_K}
    aggregate = json.loads((bundle / "aggregate.json").read_text())
    assert set(aggregate["backends"]) == {"qdrant@k1", "qdrant@k3", "buffer"}
    # Depth really changes what is retrieved: k=1 gets one exchange, k=3 gets three.
    probes = {p["backend"]: p for p in records(bundle, "probe")}
    assert probes["qdrant@k1"]["context"].count("Human: ") == 1
    assert probes["qdrant@k3"]["context"].count("Human: ") == 3
