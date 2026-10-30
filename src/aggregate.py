"""Compute benchmark metrics from a run bundle's transcript.

The aggregate is always derived from `transcript.jsonl`, never accumulated
separately, so re-scoring or re-aggregating an old bundle gives the same
numbers the run printed.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np

from src.backends.base import score_recall
from src.bundle import load_manifest, read_transcript

LABELS = ("correct", "partial", "failed")


def _dist(labels: list[str]) -> dict:
    n = len(labels)
    out = {f"{lab}_rate": (labels.count(lab) / n if n else 0.0) for lab in LABELS}
    out["n"] = n
    return out


def _std(values: list[float]) -> float:
    return float(np.std(values)) if values else 0.0


def _mean(values: list[float]) -> float:
    return float(np.mean(values)) if values else 0.0


def aggregate_records(records: list[dict], manifest: dict | None = None) -> dict:
    by_backend: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        by_backend[rec["backend"]].append(rec)

    summary: dict[str, dict] = {}
    for backend, recs in by_backend.items():
        ends = {r["run_index"]: r for r in recs if r["type"] == "run_end"}
        valid = {i for i, r in ends.items() if r.get("error") is None}
        if not valid:
            errors = sorted({r.get("error") or "incomplete" for r in ends.values()})
            summary[backend] = {"error": "All runs failed", "run_errors": errors}
            continue
        turns = [r for r in recs if r["type"] == "turn" and r["run_index"] in valid]
        probes = [r for r in recs if r["type"] == "probe" and r["run_index"] in valid]

        per_turn: dict[int, list[float]] = defaultdict(list)
        for t in turns:
            per_turn[t["turn"]].append(t["retrieve_ms"] + t["llm_ms"] + t["write_ms"])
        all_lat = [v for vals in per_turn.values() for v in vals]

        tokens_per_run: dict[int, int] = defaultdict(int)
        probe_tokens_per_run: dict[int, int] = defaultdict(int)
        for t in turns:
            tokens_per_run[t["run_index"]] += (
                t["input_tokens"] + t["output_tokens"]
                + t["write_input_tokens"] + t["write_output_tokens"]
            )
        for p in probes:
            probe_tokens_per_run[p["run_index"]] += p["input_tokens"] + p["output_tokens"]
        token_counts = [tokens_per_run[i] for i in sorted(valid)]

        by_checkpoint: dict[int, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        all_labels = []
        for p in probes:
            label = score_recall(p["response"], p["answer_key"])
            by_checkpoint[p["checkpoint"]][p["fact_id"]].append(label)
            all_labels.append(label)

        recall_by_checkpoint = {}
        for cp in sorted(by_checkpoint):
            labels = [lab for labs in by_checkpoint[cp].values() for lab in labs]
            entry = _dist(labels)
            entry["total_probes"] = entry.pop("n")
            entry["by_fact"] = {fid: _dist(labs) for fid, labs in sorted(by_checkpoint[cp].items())}
            recall_by_checkpoint[str(cp)] = entry

        overall = _dist(all_labels)
        overall["total_probes"] = overall.pop("n")

        summary[backend] = {
            "num_runs": len(ends),
            "num_valid_runs": len(valid),
            "avg_latency_ms": _mean(all_lat),
            "std_latency_ms": _std(all_lat),
            "avg_latency_per_turn": {str(t): _mean(v) for t, v in sorted(per_turn.items())},
            "recall_by_checkpoint": recall_by_checkpoint,
            "recall_overall": overall,
            "avg_tokens_per_run": _mean(token_counts),
            "std_tokens_per_run": _std(token_counts),
            "avg_probe_tokens_per_run": _mean([probe_tokens_per_run[i] for i in sorted(valid)]),
            "estimated_cost_per_1k_conversations_usd": _estimate_cost_per_1k(_mean(token_counts)),
        }

    return {
        "run_id": (manifest or {}).get("run_id"),
        "is_sample": bool((manifest or {}).get("is_sample")),
        "backends": summary,
    }


def _estimate_cost_per_1k(avg_tokens: float) -> float:
    """Blended-rate estimate kept from v1 ($3/$15 per 1M, 3:1 input:output)."""
    blended_rate_per_token = (0.003 * 0.75 + 0.015 * 0.25) / 1000
    return avg_tokens * blended_rate_per_token * 1000


def aggregate_bundle(bundle: str | Path) -> dict:
    return aggregate_records(read_transcript(bundle), load_manifest(bundle))
