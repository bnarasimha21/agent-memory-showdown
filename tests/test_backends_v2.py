"""Issue 5: backend registry, k sweep and the LangChain 1.x port (no docker needed)."""

import json
import re
from pathlib import Path

import pytest

from run_benchmark import parse_args
from src.backends.base import backend_label
from src.backends.buffer_memory import BufferMemoryBackend
from src.backends.registry import AVAILABLE_BACKENDS
from src.harness import run_benchmark
from src.visualize import BACKEND_COLORS, backend_color
from tests.helpers import records

ROOT = Path(__file__).resolve().parent.parent


class WindowBackend(BufferMemoryBackend):
    """Service-free stand-in for a top-k backend: the last k exchanges."""

    name = "window"
    uses_k = True

    def retrieve(self, query):
        result = super().retrieve(query)
        lines = result.text.split("\n")
        result.text = "\n".join(lines[-2 * self.k:])
        return result


def test_registry_has_the_six_backends_with_descriptions():
    assert list(AVAILABLE_BACKENDS) == [
        "buffer", "summary", "qdrant", "pgvector", "langgraph_store", "mem0"
    ]
    for name, cls in AVAILABLE_BACKENDS.items():
        assert cls.name == name
        assert cls.stores, name
        assert name in BACKEND_COLORS
    assert {n for n, c in AVAILABLE_BACKENDS.items() if c.uses_k} == {
        "qdrant", "pgvector", "langgraph_store", "mem0"
    }


def test_backend_label():
    qdrant = AVAILABLE_BACKENDS["qdrant"]
    assert backend_label(qdrant, 8, sweep=True) == "qdrant@k8"
    assert backend_label(qdrant, 8, sweep=False) == "qdrant"
    assert backend_label(AVAILABLE_BACKENDS["buffer"], 8, sweep=True) == "buffer"
    assert AVAILABLE_BACKENDS["buffer"](k=3).label(sweep=True) == "buffer"


def test_k_sweep_runs_each_top_k_backend_once_per_k(tmp_path):
    bundle = run_benchmark(
        [WindowBackend, AVAILABLE_BACKENDS["buffer"]], num_runs=1, num_turns=12,
        checkpoints=[12], results_dir=tmp_path, composition={"extraction": 1},
        distractors=False, judge=False, ks=[1, 3, 1],
    )
    manifest = json.loads((bundle / "manifest.json").read_text())
    assert manifest["backends"] == ["window@k1", "window@k3", "buffer"]
    assert manifest["k"] == [1, 3]  # duplicates dropped, order kept
    starts = {s["backend"]: s["k"] for s in records(bundle, "run_start")}
    assert starts["window@k1"] == 1 and starts["window@k3"] == 3
    probes = {p["backend"]: p for p in records(bundle, "probe")}
    assert probes["window@k1"]["context"].count("Human: ") == 1
    assert probes["window@k3"]["context"].count("Human: ") == 3
    aggregate = json.loads((bundle / "aggregate.json").read_text())
    assert set(aggregate["backends"]) == {"window@k1", "window@k3", "buffer"}


def test_single_k_sets_depth_without_relabelling(tmp_path):
    bundle = run_benchmark(
        [WindowBackend], num_runs=1, num_turns=12, checkpoints=[12], results_dir=tmp_path,
        composition={"extraction": 1}, distractors=False, judge=False, ks=[2],
    )
    manifest = json.loads((bundle / "manifest.json").read_text())
    assert manifest["backends"] == ["window"] and manifest["k"] == 2
    (start,) = records(bundle, "run_start")
    assert start["backend"] == "window" and start["k"] == 2


def test_non_positive_k_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="positive"):
        run_benchmark([WindowBackend], num_runs=1, num_turns=12, results_dir=tmp_path, ks=[0, 2])


def test_cli_k_option():
    assert parse_args(["--k", "2", "4", "8"]).k == [2, 4, 8]
    assert parse_args([]).k is None
    assert "langgraph_store" in parse_args([]).backends and "mem0" in parse_args([]).backends


def test_backend_color_shades_sweep_variants():
    assert backend_color("qdrant") == BACKEND_COLORS["qdrant"]
    assert backend_color("qdrant@k1") == BACKEND_COLORS["qdrant"]
    shades = [backend_color(f"qdrant@k{k}") for k in (1, 2, 4, 8)]
    assert len(set(shades)) == 4
    brightness = [sum(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in shades]
    assert brightness == sorted(brightness)  # larger k is lighter
    assert backend_color("unknown@k4").startswith("#")


LEGACY = re.compile(
    r"^\s*(from|import)\s+(langchain\.|langchain\s|langchain_community|psycopg2)"
    r"|\bConversation\w*(Chain|Memory)\(",
    re.M,
)


def test_no_legacy_langchain_or_psycopg2_imports():
    files = [ROOT / "run_benchmark.py", *ROOT.glob("src/**/*.py"), *ROOT.glob("scripts/*.py"),
             *ROOT.glob("tests/**/*.py")]
    offenders = [
        f"{f.relative_to(ROOT)}: {m.group(0).strip()}"
        for f in files if f.name != Path(__file__).name
        for m in LEGACY.finditer(f.read_text())
    ]
    assert offenders == []
    reqs = (ROOT / "requirements.txt").read_text().splitlines()
    names = {re.split(r"[<>=\[ ]", r, maxsplit=1)[0] for r in reqs if r and not r.startswith("#")}
    assert not names & {"langchain", "langchain-community", "psycopg2-binary"}
    assert {"langchain-core", "langgraph", "mem0ai", "psycopg"} <= names
