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

from src.bundle import load_manifest, validate_run_id

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
        # The aggregate decides from the scoring actually in effect (a rescore
        # with a fake judge is a sample); older aggregates fall back to the manifest.
        if "is_sample" in self.aggregate:
            return bool(self.aggregate["is_sample"])
        return bool(self.manifest.get("is_sample"))

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
        try:
            validate_run_id(run_id)
        except ValueError as exc:
            raise ValueError(f"invalid run id in {latest}: {run_id!r}") from exc
        bundles.append(load_bundle(runs_dir / run_id))
    return bundles


def load_legacy(path: Path = LEGACY_V1) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def headline_row(data: dict) -> dict:
    """The few numbers every summary shows for one backend label of an aggregate."""
    if "error" in data:
        return {"error": data["error"]}
    overall = data.get("recall_overall") or {}
    run_mean = data.get("recall_run_mean") or {}
    cost = data.get("cost") or {}
    total = (data.get("latency") or {}).get("total_ms") or {}
    memory = data.get("memory_size_end") or {}
    return {
        "error": None,
        "recall": overall.get("correct_rate"),
        "recall_ci": overall.get("correct_ci95"),
        "headline_n": overall.get("n", 0),
        "probes_all": sum(d["n"] for d in (data.get("recall_by_category") or {}).values()),
        "run_mean": run_mean.get("mean"),
        "run_mean_ci": run_mean.get("ci95"),
        "runs": data.get("num_valid_runs"),
        "runs_used": run_mean.get("n"),
        "cost_per_1k": cost.get("per_1k_conversations_usd"),
        "cost_per_correct": cost.get("per_correct_recall_usd"),
        "latency_p50": total.get("p50"),
        "latency_p95": total.get("p95"),
        "tokens": (data.get("tokens") or {}).get("total_tokens"),
        "memory_end": memory.get("mean"),
        "memory_unit": memory.get("unit"),
    }


def seed_pairing(bundle: Bundle) -> dict | None:
    """How the backends' runs line up, in words both the site and the README use.

    `kind` is "paired" (every backend scored on the same runs), "unpaired"
    (no run completed everywhere, so each backend uses its own runs and the
    comparison is not like for like), or None for a bundle aggregated before
    pairing was recorded. `text` is one sentence; `warning` is set for the
    unpaired case and when runs were dropped.
    """
    seeds = bundle.aggregate.get("seeds")
    if not seeds:
        return None
    manifest_seeds = bundle.manifest.get("seeds") or []

    def runs_text(runs) -> str:
        return ", ".join(
            f"{i} (seed {manifest_seeds[i]})" if isinstance(i, int) and i < len(manifest_seeds) else str(i)
            for i in runs) or "none"

    dropped = seeds.get("dropped") or {}
    dropped_text = "; ".join(f"{b}: run {', '.join(str(i) for i in v)}" for b, v in sorted(dropped.items()))
    if seeds.get("paired"):
        text = f"Seeds paired: every backend is scored on runs {runs_text(seeds.get('runs') or [])}."
        warning = None
        if dropped:
            text += f" Dropped because the run failed for another backend: {dropped_text}."
            warning = ("Some runs were dropped so that every backend is compared on the same "
                       f"conversations ({dropped_text}).")
        return {"kind": "paired", "paired": True, "runs": seeds.get("runs"), "dropped": dropped,
                "text": text, "warning": warning}
    per_backend = {label: data.get("runs_used") for label, data in bundle.backends.items()
                   if "error" not in data}
    used = "; ".join(f"{b}: {runs_text(r or [])}" for b, r in per_backend.items())
    text = ("Seeds NOT paired: no run completed for every backend, so each backend is scored on "
            f"its own runs ({used}).")
    return {"kind": "unpaired", "paired": False, "runs": None, "dropped": dropped,
            "runs_by_backend": per_backend, "text": text,
            "warning": ("UNPAIRED: the backends are not compared on the same conversations, so "
                        "differences between them mix the backend with the dataset. " + text)}
