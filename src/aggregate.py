"""Compute benchmark metrics from a run bundle.

The aggregate is always derived from `transcript.jsonl` (plus `scores.jsonl`
when present), never accumulated separately, so re-aggregating an old bundle
gives the same numbers the run printed.

Latency is split into retrieve_ms (memory lookup), llm_ms (the answering call)
and write_ms (storing the exchange, including any summarizer call), each with
p50/p95 over conversation turns; probes are timed separately. Cost uses the
recorded input and output tokens and the model's prices in pricing.yaml.
Conversation cost covers the answering calls and memory maintenance (the
summarizer); probe calls are reported separately and only enter cost per
correct recall, which is (conversation + probe spend) / correct probes.

Recall figures use the judge label when the bundle was judged (falling back to
the matcher label for probes the judge could not score) and the matcher label
otherwise; both scorers' figures are always reported. Every rate carries a 95%
Wilson interval over probes. Probes from the same run are not independent, so
the per-run recall mean with a bootstrap interval over runs is reported too;
it is the more honest interval for comparing backends.

Recall is broken down by fact category (`recall_by_category`). The headline
figures (`recall_overall`, `recall_by_checkpoint`, `recall_run_mean`) leave out
the `sensitive` category, which is reported on its own as `recall_sensitive`,
because whether a model repeats a password back is a safety behaviour rather
than a memory result. Abstention probes count as correct when the model says it
was not told. Cost per correct recall divides all spend by correct probes of
every category.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from src.bundle import load_manifest, read_transcript
from src.dataset import CATEGORIES, NON_HEADLINE, probe_category
from src.pricing import Price, price_for
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


COMPONENTS = ("retrieve_ms", "llm_ms", "write_ms")


def _pcts(values: list[float]) -> dict:
    if not values:
        return {"p50": 0.0, "p95": 0.0, "mean": 0.0, "n": 0}
    arr = np.asarray(values, dtype=float)
    return {
        "p50": float(np.percentile(arr, 50)),
        "p95": float(np.percentile(arr, 95)),
        "mean": float(arr.mean()),
        "n": int(arr.size),
    }


def _latency(rows: list[dict]) -> dict:
    out = {c: _pcts([r.get(c, 0.0) for r in rows]) for c in COMPONENTS}
    out["total_ms"] = _pcts([sum(r.get(c, 0.0) for c in COMPONENTS) for r in rows])
    return out


def _cost(price: Price | None, input_tokens: float, output_tokens: float) -> float | None:
    return price.cost(input_tokens, output_tokens) if price is not None else None


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

    model = (manifest or {}).get("llm_model")
    price = price_for(model)

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

        runs = sorted(valid)
        turns_by_number: dict[int, list[dict]] = defaultdict(list)
        for t in turns:
            turns_by_number[t["turn"]].append(t)
        latency_by_turn = {
            str(n): {c: _mean([r[c] for r in rows]) for c in COMPONENTS}
            for n, rows in sorted(turns_by_number.items())
        }

        # Tokens per run. "chat" = the answering call of each conversation turn;
        # "memory" = calls the backend makes to maintain memory (the summarizer);
        # "probe" = recall questions, which are not part of the conversation.
        tok = {i: defaultdict(int) for i in runs}
        for t in turns:
            d = tok[t["run_index"]]
            d["chat_input"] += t["input_tokens"]
            d["chat_output"] += t["output_tokens"]
            d["chat_calls"] += 1
            d["memory_input"] += t["write_input_tokens"]
            d["memory_output"] += t["write_output_tokens"]
            d["memory_calls"] += t["write_llm_calls"]
        for p in probes:
            d = tok[p["run_index"]]
            d["probe_input"] += p["input_tokens"]
            d["probe_output"] += p["output_tokens"]
            d["probe_calls"] += 1

        def per_run(key: str) -> list[float]:
            return [tok[i][key] for i in runs]

        conv_in = [tok[i]["chat_input"] + tok[i]["memory_input"] for i in runs]
        conv_out = [tok[i]["chat_output"] + tok[i]["memory_output"] for i in runs]
        token_counts = [a + b for a, b in zip(conv_in, conv_out)]
        tokens = {
            "input_tokens": _mean(conv_in),
            "output_tokens": _mean(conv_out),
            "total_tokens": _mean(token_counts),
            "chat": {"calls": _mean(per_run("chat_calls")), "input_tokens": _mean(per_run("chat_input")),
                     "output_tokens": _mean(per_run("chat_output"))},
            "memory": {"calls": _mean(per_run("memory_calls")),
                       "input_tokens": _mean(per_run("memory_input")),
                       "output_tokens": _mean(per_run("memory_output"))},
            "probe": {"calls": _mean(per_run("probe_calls")), "input_tokens": _mean(per_run("probe_input")),
                      "output_tokens": _mean(per_run("probe_output"))},
        }

        conv_costs = [_cost(price, a, b) for a, b in zip(conv_in, conv_out)]
        memory_cost = _cost(price, tokens["memory"]["input_tokens"], tokens["memory"]["output_tokens"])
        probe_cost_total = _cost(price, sum(per_run("probe_input")), sum(per_run("probe_output")))

        sizes = [ends[i].get("memory_stats") or {} for i in runs]
        sizes = [m for m in sizes if "size" in m]
        memory_size = (
            {"mean": _mean([m["size"] for m in sizes]), "max": max(m["size"] for m in sizes),
             "unit": sizes[0]["unit"]}
            if sizes else None
        )

        by_checkpoint: dict[int, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        by_run: dict[int, list[str]] = defaultdict(list)
        by_category: dict[str, list[str]] = defaultdict(list)
        matcher_by_category: dict[str, list[str]] = defaultdict(list)
        all_labels: list[str] = []
        primary_labels, matcher_labels, judge_labels = [], [], []
        pairs: list[tuple[str, str]] = []
        judge_errors = 0
        judge_in = judge_out = 0
        for p in probes:
            score = score_by_key.get(score_key(p))
            if score is None:  # a probe without a score: score it with the matcher now
                score = score_probes([p])[0]
            label = _primary(score, judged)
            category = probe_category(p)
            headline = category not in NON_HEADLINE
            all_labels.append(label)
            by_category[category].append(label)
            matcher_by_category[category].append(score["matcher_label"])
            if headline:
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
                if headline:
                    judge_labels.append(jl)
                pairs.append((score["matcher_label"], jl))
                if jl != score["matcher_label"]:
                    disagreements.append({
                        "backend": backend, "run_index": p["run_index"],
                        "checkpoint": p["checkpoint"], "fact_id": p["fact_id"],
                        "category": category, "question": p["question"], "response": p["response"],
                        "matcher_label": score["matcher_label"], "judge_label": jl,
                        "judge_rationale": score.get("judge_rationale"),
                    })
            probe_rows.append({
                "backend": backend, "run_index": p["run_index"], "checkpoint": p["checkpoint"],
                "fact_id": p["fact_id"], "category": category, "label": label,
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

        n_correct = all_labels.count("correct")
        order = [c for c in CATEGORIES if c in by_category] + sorted(set(by_category) - set(CATEGORIES))
        if price is not None:
            total_spend = sum(conv_costs) + (probe_cost_total or 0.0)
            cost_per_correct = total_spend / n_correct if n_correct else None
            cost_per_conv = _mean(conv_costs)
            cost = {
                "per_conversation_usd": cost_per_conv,
                "per_conversation_ci95": bootstrap_mean(conv_costs)["ci95"],
                "per_1k_conversations_usd": cost_per_conv * 1000,
                "memory_maintenance_per_conversation_usd": memory_cost,
                "probes_per_run_usd": (probe_cost_total or 0.0) / len(runs),
                "per_correct_recall_usd": cost_per_correct,
            }
        else:
            cost = None

        summary[backend] = {
            "num_runs": len(ends),
            "num_valid_runs": len(valid),
            "scorer": "judge" if judged else "matcher",
            "latency": _latency(turns),
            "probe_latency": _latency(probes),
            "latency_by_turn": latency_by_turn,
            "tokens": tokens,
            "cost": cost,
            "memory_size_end": memory_size,
            "recall_by_checkpoint": recall_by_checkpoint,
            "recall_overall": _dist(primary_labels),
            "recall_run_mean": bootstrap_mean(run_rates),
            "recall_by_category": {c: _dist(by_category[c]) for c in order},
            "recall_sensitive": (
                _dist([lab for c in NON_HEADLINE for lab in by_category.get(c, [])])
                if any(c in by_category for c in NON_HEADLINE) else None
            ),
            "matcher": {"recall_overall": _dist(matcher_labels),
                        "recall_by_category": {c: _dist(matcher_by_category[c]) for c in order}},
            "judge": (
                {"recall_overall": _dist(judge_labels), "errors": judge_errors,
                 "input_tokens": judge_in, "output_tokens": judge_out}
                if judged else None
            ),
            "agreement": _agreement(pairs) if judged else None,
            "tokens_per_run": bootstrap_mean(token_counts),
            "std_tokens_per_run": _std(token_counts),
        }

    return {
        "run_id": (manifest or {}).get("run_id"),
        "is_sample": bool((manifest or {}).get("is_sample")),
        "scoring": scoring or (manifest or {}).get("scoring"),
        "pricing": (
            {**price.to_dict(), "formula": "input_tokens * input_per_mtok / 1e6 + "
                                           "output_tokens * output_per_mtok / 1e6"}
            if price is not None else {"model": model, "unpriced": True}
        ),
        "headline": {"excludes_categories": sorted(NON_HEADLINE)},
        "agreement": {**_agreement(all_pairs), "disagreement_list": disagreements} if judged else None,
        "backends": summary,
        "probes": probe_rows,
    }


def aggregate_bundle(bundle: str | Path) -> dict:
    from src.scoring.rescore import load_scores, load_scoring_info

    return aggregate_records(
        read_transcript(bundle), load_manifest(bundle),
        scores=load_scores(bundle), scoring=load_scoring_info(bundle),
    )
