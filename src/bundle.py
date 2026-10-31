"""Run bundles: everything needed to audit and re-score a benchmark run.

Layout of `results/runs/<run_id>/`:

- `manifest.json`     how the run was produced (git sha, models, k, seeds,
                      prompt hash, package versions, timing)
- `dataset.json`      the realized dataset for every run index
- `transcript.jsonl`  one JSON object per line: run_start, turn, checkpoint,
                      probe and run_end records, with inputs, retrieved
                      context, responses, tokens and timings
- `scores.jsonl`      matcher and judge label for every probe
- `scoring.json`      matcher version, judge provider/model and prompt hash
- `aggregate.json`    metrics computed from the transcript and scores

The transcript is written line by line as the run progresses, so a crashed
run still leaves an inspectable partial bundle. A published bundle may carry
`transcript.jsonl.gz` instead (see `python -m src.site.publish`); every reader
goes through `iter_transcript`, which accepts either.
"""

from __future__ import annotations

import gzip
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Iterator

TRACKED_PACKAGES = [
    "langchain-core",
    "langchain-huggingface",
    "langchain-openai",
    "langchain-qdrant",
    "langchain-postgres",
    "langgraph",
    "langgraph-checkpoint-postgres",
    "mem0ai",
    "qdrant-client",
    "psycopg",
    "sentence-transformers",
    "numpy",
    "plotly",
]

REPO_ROOT = Path(__file__).resolve().parent.parent


def git_info() -> dict:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()

    try:
        sha = run("rev-parse", "HEAD")
        dirty = bool(run("status", "--porcelain", "--untracked-files=no"))
        return {"sha": sha, "dirty": dirty}
    except (OSError, subprocess.CalledProcessError):
        return {"sha": None, "dirty": None}


def package_versions() -> dict:
    versions = {}
    for name in TRACKED_PACKAGES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
    return versions


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_run_id(label: str | None = None) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{stamp}-{label}" if label else stamp


def environment_info() -> dict:
    return {"python": sys.version.split()[0], "platform": platform.platform()}


class BundleWriter:
    def __init__(self, root: str | Path, run_id: str, manifest: dict) -> None:
        self.run_id = run_id
        self.path = Path(root) / run_id
        self.path.mkdir(parents=True, exist_ok=False)
        self.manifest = dict(manifest, run_id=run_id)
        self._write_json("manifest.json", self.manifest)
        self._transcript = open(self.path / "transcript.jsonl", "a", encoding="utf-8")

    def write_json(self, name: str, data: Any) -> None:
        self._write_json(name, data)

    def close_transcript(self) -> None:
        if not self._transcript.closed:
            self._transcript.close()

    def _write_json(self, name: str, data: Any) -> None:
        (self.path / name).write_text(
            json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
            encoding="utf-8",
        )

    def write_dataset(self, datasets: dict) -> None:
        self._write_json("dataset.json", datasets)

    def record(self, record: dict) -> None:
        self._transcript.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._transcript.flush()

    def finalize(self, **manifest_updates: Any) -> None:
        self.close_transcript()
        self.manifest.update(manifest_updates)
        self._write_json("manifest.json", self.manifest)

    def write_aggregate(self, aggregate: dict) -> Path:
        self._write_json("aggregate.json", aggregate)
        return self.path / "aggregate.json"


def load_manifest(bundle: str | Path) -> dict:
    return json.loads((Path(bundle) / "manifest.json").read_text(encoding="utf-8"))


def load_dataset(bundle: str | Path) -> dict:
    path = Path(bundle) / "dataset.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


TRANSCRIPT = "transcript.jsonl"
TRANSCRIPT_GZ = "transcript.jsonl.gz"


def transcript_path(bundle: str | Path) -> Path:
    """The bundle's transcript, plain or gzipped. Raises if it has neither."""
    bundle = Path(bundle)
    for name in (TRANSCRIPT, TRANSCRIPT_GZ):
        if (bundle / name).exists():
            return bundle / name
    raise FileNotFoundError(f"{bundle} has no {TRANSCRIPT} or {TRANSCRIPT_GZ}")


def iter_transcript(bundle: str | Path) -> Iterator[dict]:
    path = transcript_path(bundle)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def read_transcript(bundle: str | Path) -> list[dict]:
    return list(iter_transcript(bundle))
