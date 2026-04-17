"""Benchmark harness: runs all backends against the dataset with inline recall probing."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Type

import numpy as np

from src.backends.base import (
    BaseMemoryBackend,
    RunResult,
    TurnMetrics,
    RecallResult,
    score_recall,
)
from src.dataset import ConversationDataset, generate_dataset
from src.config import config

logger = logging.getLogger(__name__)


def run_single(
    backend_cls: Type[BaseMemoryBackend],
    dataset: ConversationDataset,
    run_index: int,
) -> RunResult:
    backend = backend_cls()
    result = RunResult(
        backend_name=backend.name,
        run_index=run_index,
        session_id=backend.session_id,
    )

    try:
        backend.setup()

        for turn in dataset.turns:
            if turn.is_recall_turn:
                for probe_info in turn.recall_probes:
                    probe_response, probe_tokens, _ = backend.timed_chat(
                        probe_info["probe"]
                    )
                    score = score_recall(probe_response, probe_info["answer_key"])
                    result.recall_results.append(
                        RecallResult(
                            probe=probe_info["probe"],
                            seeded_at_turn=probe_info["seeded_at_turn"],
                            probed_at_turn=turn.turn_number,
                            response=probe_response,
                            score=score,
                            answer_key=probe_info["answer_key"],
                        )
                    )
                    result.total_tokens += probe_tokens
            else:
                _response, tokens, latency_ms = backend.timed_chat(turn.human_message)
                result.turn_metrics.append(
                    TurnMetrics(
                        turn_number=turn.turn_number,
                        retrieval_latency_ms=latency_ms,
                        tokens_used=tokens,
                    )
                )
                result.total_tokens += tokens

    except Exception as exc:
        logger.error(
            "Backend %s run %d failed: %s", backend.name, run_index, exc, exc_info=True
        )
        result.error = str(exc)
    finally:
        try:
            backend.teardown()
        except Exception:
            pass

    return result


def run_benchmark(
    backend_classes: list[Type[BaseMemoryBackend]],
    num_runs: int | None = None,
    num_turns: int | None = None,
    seed_turns: list[int] | None = None,
    recall_turns: list[int] | None = None,
) -> dict:
    num_runs = num_runs or config.NUM_RUNS
    num_turns = num_turns or config.NUM_TURNS
    seed_turns = seed_turns or config.SEED_TURNS
    recall_turns = recall_turns or config.RECALL_TURNS

    all_results: dict[str, list[RunResult]] = {
        cls.name: [] for cls in backend_classes
    }

    for backend_cls in backend_classes:
        logger.info("Benchmarking backend: %s", backend_cls.name)
        for run_idx in range(num_runs):
            dataset = generate_dataset(
                num_turns=num_turns,
                seed_turns=seed_turns,
                recall_turns=recall_turns,
                random_seed=42 + run_idx,
            )
            logger.info("  Run %d / %d", run_idx + 1, num_runs)
            run_result = run_single(backend_cls, dataset, run_idx)
            all_results[backend_cls.name].append(run_result)

    return aggregate_results(all_results)


def aggregate_results(all_results: dict[str, list[RunResult]]) -> dict:
    summary = {}

    for backend_name, runs in all_results.items():
        valid_runs = [r for r in runs if r.error is None]
        if not valid_runs:
            summary[backend_name] = {"error": "All runs failed"}
            continue

        turn_latencies: dict[int, list[float]] = {}
        for run in valid_runs:
            for tm in run.turn_metrics:
                turn_latencies.setdefault(tm.turn_number, []).append(
                    tm.retrieval_latency_ms
                )

        avg_latency_per_turn = {
            t: float(np.mean(lats)) for t, lats in sorted(turn_latencies.items())
        }
        overall_latency_values = [
            lat for lats in turn_latencies.values() for lat in lats
        ]

        # Recall by (probed_at_turn, seeded_at_turn) for the decay curve
        recall_by_probe_turn: dict[int, dict[int, list[str]]] = {}
        for run in valid_runs:
            for rr in run.recall_results:
                recall_by_probe_turn.setdefault(rr.probed_at_turn, {}).setdefault(
                    rr.seeded_at_turn, []
                ).append(rr.score)

        recall_accuracy = {}
        for probe_turn in sorted(recall_by_probe_turn):
            seeds = recall_by_probe_turn[probe_turn]
            all_scores = [s for scores in seeds.values() for s in scores]
            correct = all_scores.count("correct")
            partial = all_scores.count("partial")
            total = len(all_scores)
            recall_accuracy[probe_turn] = {
                "correct_rate": correct / total if total else 0,
                "partial_rate": partial / total if total else 0,
                "failed_rate": (total - correct - partial) / total if total else 0,
                "total_probes": total,
                "by_seed_turn": {
                    seed_t: _score_dist(scores)
                    for seed_t, scores in sorted(seeds.items())
                },
            }

        token_counts = [r.total_tokens for r in valid_runs]
        cost_per_1k = _estimate_cost_per_1k(float(np.mean(token_counts)))

        summary[backend_name] = {
            "num_valid_runs": len(valid_runs),
            "avg_latency_ms": float(np.mean(overall_latency_values)) if overall_latency_values else 0,
            "std_latency_ms": float(np.std(overall_latency_values)) if overall_latency_values else 0,
            "avg_latency_per_turn": avg_latency_per_turn,
            "recall_accuracy_by_probe_turn": recall_accuracy,
            "avg_tokens_per_run": float(np.mean(token_counts)),
            "std_tokens_per_run": float(np.std(token_counts)),
            "estimated_cost_per_1k_conversations_usd": cost_per_1k,
        }

    return summary


def _score_dist(scores: list[str]) -> dict:
    correct = scores.count("correct")
    partial = scores.count("partial")
    total = len(scores)
    return {
        "correct_rate": correct / total if total else 0,
        "partial_rate": partial / total if total else 0,
        "failed_rate": (total - correct - partial) / total if total else 0,
        "n": total,
    }


def _estimate_cost_per_1k(avg_tokens: float) -> float:
    """Cost estimate using Claude 3.5 Sonnet pricing via DO Serverless Inference.

    DO pricing for claude-3.5-sonnet:
      Input:  $0.003  / 1K tokens
      Output: $0.015  / 1K tokens
    We approximate a 3:1 input:output ratio to get a blended rate.
    """
    blended_rate_per_token = (0.003 * 0.75 + 0.015 * 0.25) / 1000
    return avg_tokens * blended_rate_per_token * 1000


def save_results(results: dict, results_dir: str | None = None) -> Path:
    results_dir = Path(results_dir or config.RESULTS_DIR)
    results_dir.mkdir(parents=True, exist_ok=True)

    timestamp = int(time.time())
    output_path = results_dir / f"benchmark_{timestamp}.json"

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    logger.info("Results saved to %s", output_path)
    return output_path
