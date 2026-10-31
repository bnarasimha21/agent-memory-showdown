"""Loading the committed run bundles and the v1 published numbers.

`results/latest.json` lists the bundles that are published, by run id, the
first being the headline run:

    {"runs": ["20261031T...-sample-fake"]}

Each id is a directory under `results/runs/`. Nothing here touches the network.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from src.bundle import load_manifest

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "results"
RUNS_DIR = RESULTS_DIR / "runs"
LATEST = RESULTS_DIR / "latest.json"
LEGACY_V1 = RESULTS_DIR / "legacy" / "v1_published.json"
PAGES_URL = "https://bnarasimha21.github.io/agent-memory-showdown/"


@dataclass
class Bundle:
    path: Path
    manifest: dict
    aggregate: dict
    run_id: str = field(init=False)

    def __post_init__(self) -> None:
        self.run_id = self.manifest.get("run_id", self.path.name)

    @property
    def is_sample(self) -> bool:
        return bool(self.manifest.get("is_sample") or self.aggregate.get("is_sample"))

    @property
    def backends(self) -> dict:
        """Aggregate per backend label, in the order the manifest lists them."""
        found = self.aggregate.get("backends", {})
        order = [b for b in self.manifest.get("backends", []) if b in found]
        return {b: found[b] for b in order + [b for b in found if b not in order]}


def load_bundle(path: str | Path) -> Bundle:
    path = Path(path)
    aggregate_path = path / "aggregate.json"
    if not aggregate_path.exists():
        raise FileNotFoundError(f"{path} has no aggregate.json; is it a finished run bundle?")
    return Bundle(path, load_manifest(path), json.loads(aggregate_path.read_text(encoding="utf-8")))


def read_latest(latest: Path = LATEST) -> list[str]:
    if not latest.exists():
        raise FileNotFoundError(
            f"{latest} not found; publish a bundle with `python -m src.site.publish results/runs/<id>`"
        )
    runs = json.loads(latest.read_text(encoding="utf-8")).get("runs") or []
    if not runs or not all(isinstance(r, str) and r for r in runs):
        raise ValueError(f"{latest} must hold a non-empty list of run ids under 'runs'")
    return runs


def published_bundles(latest: Path = LATEST, runs_dir: Path = RUNS_DIR) -> list[Bundle]:
    """The bundles listed in latest.json, headline first."""
    bundles = []
    for run_id in read_latest(latest):
        if "/" in run_id or "\\" in run_id or run_id in (".", ".."):
            raise ValueError(f"invalid run id in {latest}: {run_id!r}")
        bundles.append(load_bundle(runs_dir / run_id))
    return bundles


def load_legacy(path: Path = LEGACY_V1) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def headline_row(data: dict) -> dict:
    """The few numbers every summary shows for one backend label of an aggregate."""
    if "error" in data:
        return {"error": data["error"]}
    overall = data["recall_overall"]
    run_mean = data.get("recall_run_mean") or {}
    cost = data.get("cost") or {}
    total = data["latency"]["total_ms"]
    return {
        "error": None,
        "recall": overall["correct_rate"],
        "recall_ci": overall["correct_ci95"],
        "headline_n": overall["n"],
        "probes_all": sum(d["n"] for d in data.get("recall_by_category", {}).values()) or overall["n"],
        "run_mean": run_mean.get("mean"),
        "run_mean_ci": run_mean.get("ci95"),
        "runs": data.get("num_valid_runs"),
        "cost_per_1k": cost.get("per_1k_conversations_usd"),
        "cost_per_correct": cost.get("per_correct_recall_usd"),
        "latency_p50": total["p50"],
        "latency_p95": total["p95"],
        "tokens": data["tokens"]["total_tokens"],
        "memory_end": data["memory_size_end"]["mean"],
        "memory_unit": data["memory_size_end"]["unit"],
    }
