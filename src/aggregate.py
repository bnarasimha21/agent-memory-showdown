"""Compute benchmark metrics from a run bundle.

The aggregate is always derived from `transcript.jsonl` (plus `scores.jsonl`
when present), never accumulated separately, so re-aggregating an old bundle
gives the same numbers the run printed.

Recall figures use the judge label when the bundle was judged (falling back to
the matcher label for probes the judge could not score) and the matcher label
otherwise; both scorers' figures are always reported. Every rate carries a 95%
Wilson interval over probes. Probes from the same run are not independent, so
the per-run recall mean with a bootstrap interval over runs is reported too;
it is the more honest interval for comparing backends.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from src.bundle import load_manifest, read_transcript
from src.scoring import LABELS
from src.stats import bootstrap_mean, cohen_kappa, wilson


def _dist(labels: list[str]) -> dict:
    n = len(labels)
    counts = Counter(labels)
    out: dict = {"n": n, "counts": {lab: counts.get(lab, 0) for lab in LABELS}}
    for lab in LABELS:
        out[f"{lab}_rate"] = counts.get(lab, 0) / n if n else 0.0
        out[f"{lab}_ci95"] = wilson(counts.get(lab, 0), n)
    return out


def _std(values: list[float]) -> float:
    return float(np.std(values)) if values else 0.0


def _mean(values: list[float]) -> float:
    return float(np.mean(values)) if values else 0.0


def _agreement(pairs: list[tuple[str, str]]) -> dict:
    matcher = [m for m, _ in pairs]
    judge = [j for _, j in pairs]
    n = len(pairs)
    return {
        "n": n,
        "observed": (sum(m == j for m, j in pairs) / n) if n else None,
        "kappa": cohen_kappa(matcher, judge),
        "disagreements": sum(m != j for m, j in pairs),
    }


def _primary(score: dict, judged: bool) -> str:
    if judged and score.get("judge_label") not in (None, "error"):
        return score["judge_label"]
    return score["matcher_label"]


def aggregate_records(
    records: list[dict],
    manifest: dict | None = None,
    scores: list[dict] | None = None,
    scoring: dict | None = None,
) -> dict:
    from src.scoring.rescore import score_key, score_probes

    if scores is None:
        scores = score_probes(records)
    score_by_key = {score_key(s): s for s in scores}
    judged = any(s.get("judge_label") is not None for s in scores)

    by_backend: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        by_backend[rec["backend"]].append(rec)

    summary: dict[str, dict] = {}
    probe_rows: list[dict] = []
    all_pairs: list[tuple[str, str]] = []
    disagreements: list[dict] = []

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
        by_run: dict[int, list[str]] = defaultdict(list)
        primary_labels, matcher_labels, judge_labels = [], [], []
        pairs: list[tuple[str, str]] = []
        judge_errors = 0
        judge_in = judge_out = 0
        for p in probes:
            score = score_by_key.get(score_key(p))
            if score is None:  # a probe without a score: score it with the matcher now
                score = score_probes([p])[0]
            label = _primary(score, judged)
            primary_labels.append(label)
            matcher_labels.append(score["matcher_label"])
            by_checkpoint[p["checkpoint"]][p["fact_id"]].append(label)
            by_run[p["run_index"]].append(label)
            jl = score.get("judge_label")
            judge_in += score.get("judge_input_tokens", 0)
            judge_out += score.get("judge_output_tokens", 0)
            if jl == "error":
                judge_errors += 1
            elif jl is not None:
                judge_labels.append(jl)
                pairs.append((score["matcher_label"], jl))
                if jl != score["matcher_label"]:
                    disagreements.append({
                        "backend": backend, "run_index": p["run_index"],
                        "checkpoint": p["checkpoint"], "fact_id": p["fact_id"],
                        "question": p["question"], "response": p["response"],
                        "matcher_label": score["matcher_label"], "judge_label": jl,
                        "judge_rationale": score.get("judge_rationale"),
                    })
            probe_rows.append({
                "backend": backend, "run_index": p["run_index"], "checkpoint": p["checkpoint"],
                "fact_id": p["fact_id"], "label": label,
                "matcher_label": score["matcher_label"], "judge_label": jl,
                "judge_rationale": score.get("judge_rationale"),
            })
        all_pairs.extend(pairs)

        recall_by_checkpoint = {}
        for cp in sorted(by_checkpoint):
            labels = [lab for labs in by_checkpoint[cp].values() for lab in labs]
            entry = _dist(labels)
            entry["by_fact"] = {fid: _dist(labs) for fid, labs in sorted(by_checkpoint[cp].items())}
            recall_by_checkpoint[str(cp)] = entry

        run_rates = [
            (by_run[i].count("correct") / len(by_run[i])) for i in sorted(valid) if by_run[i]
        ]

        summary[backend] = {
            "num_runs": len(ends),
            "num_valid_runs": len(valid),
            "scorer": "judge" if judged else "matcher",
            "avg_latency_ms": _mean(all_lat),
            "std_latency_ms": _std(all_lat),
            "avg_latency_per_turn": {str(t): _mean(v) for t, v in sorted(per_turn.items())},
            "recall_by_checkpoint": recall_by_checkpoint,
            "recall_overall": _dist(primary_labels),
            "recall_run_mean": bootstrap_mean(run_rates),
            "matcher": {"recall_overall": _dist(matcher_labels)},
            "judge": (
                {"recall_overall": _dist(judge_labels), "errors": judge_errors,
                 "input_tokens": judge_in, "output_tokens": judge_out}
                if judged else None
            ),
            "agreement": _agreement(pairs) if judged else None,
            "avg_tokens_per_run": _mean(token_counts),
            "std_tokens_per_run": _std(token_counts),
            "tokens_per_run": bootstrap_mean(token_counts),
            "avg_probe_tokens_per_run": _mean([probe_tokens_per_run[i] for i in sorted(valid)]),
            "estimated_cost_per_1k_conversations_usd": _estimate_cost_per_1k(_mean(token_counts)),
        }

    return {
        "run_id": (manifest or {}).get("run_id"),
        "is_sample": bool((manifest or {}).get("is_sample")),
        "scoring": scoring or (manifest or {}).get("scoring"),
        "agreement": {**_agreement(all_pairs), "disagreement_list": disagreements} if judged else None,
        "backends": summary,
        "probes": probe_rows,
    }


def _estimate_cost_per_1k(avg_tokens: float) -> float:
    """Blended-rate estimate kept from v1 ($3/$15 per 1M, 3:1 input:output)."""
    blended_rate_per_token = (0.003 * 0.75 + 0.015 * 0.25) / 1000
    return avg_tokens * blended_rate_per_token * 1000


def aggregate_bundle(bundle: str | Path) -> dict:
    from src.scoring.rescore import load_scores, load_scoring_info

    return aggregate_records(
        read_transcript(bundle), load_manifest(bundle),
        scores=load_scores(bundle), scoring=load_scoring_info(bundle),
    )
