"""Benchmark harness: runs all backends against the dataset."""

from __future__ import annotations

import json
import logging
import os
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

        # Run through all 50 conversation turns
        for turn in dataset.turns:
            response, tokens, latency_ms = backend.timed_chat(turn.human_message)
            result.turn_metrics.append(
                TurnMetrics(
                    turn_number=turn.turn_number,
                    retrieval_latency_ms=latency_ms,
                    tokens_used=tokens,
                )
            )
            result.total_tokens += tokens

        # Recall probes at the end
        for probe_info in dataset.recall_probes:
            probe_response, _, _ = backend.timed_chat(probe_info["probe"])
            score = score_recall(probe_response, probe_info["answer_key"])
            result.recall_results.append(
                RecallResult(
                    probe=probe_info["probe"],
                    seeded_at_turn=probe_info["seeded_at_turn"],
                    response=probe_response,
                    score=score,
                    answer_key=probe_info["answer_key"],
                )
            )

    except Exception as exc:
        logger.error(
            "Backend %s run %d failed: %s", backend.name, run_index, exc
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
    num_runs: int = None,
    num_turns: int = None,
    seed_turns: list[int] = None,
) -> dict:
    num_runs = num_runs or config.NUM_RUNS
    num_turns = num_turns or config.NUM_TURNS
    seed_turns = seed_turns or config.SEED_TURNS

    all_results: dict[str, list[RunResult]] = {
        cls.name: [] for cls in backend_classes
    }

    dataset = generate_dataset(num_turns=num_turns, seed_turns=seed_turns)

    for backend_cls in backend_classes:
        logger.info("Benchmarking backend: %s", backend_cls.name)
        for run_idx in range(num_runs):
            logger.info("  Run %d / %d", run_idx + 1, num_runs)
            run_result = run_single(backend_cls, dataset, run_idx)
            all_results[backend_cls.name].append(run_result)

    return aggregate_results(all_results, num_runs, seed_turns)


def aggregate_results(
    all_results: dict[str, list[RunResult]],
    num_runs: int,
    seed_turns: list[int],
) -> dict:
    summary = {}

    for backend_name, runs in all_results.items():
        valid_runs = [r for r in runs if r.error is None]
        if not valid_runs:
            summary[backend_name] = {"error": "All runs failed"}
            continue

        # Per-turn latency stats
        turn_latencies: dict[int, list[float]] = {}
        for run in valid_runs:
            for tm in run.turn_metrics:
                turn_latencies.setdefault(tm.turn_number, []).append(
                    tm.retrieval_latency_ms
                )

        avg_latency_per_turn = {
            t: float(np.mean(lats)) for t, lats in turn_latencies.items()
        }
        overall_latency_values = [
            lat for lats in turn_latencies.values() for lat in lats
        ]

        # Recall scoring
        recall_by_seed: dict[int, list[str]] = {}
        for run in valid_runs:
            for rr in run.recall_results:
                recall_by_seed.setdefault(rr.seeded_at_turn, []).append(rr.score)

        recall_accuracy_by_seed = {}
        for seed_turn, scores in recall_by_seed.items():
            correct = scores.count("correct")
            partial = scores.count("partial")
            total = len(scores)
            recall_accuracy_by_seed[seed_turn] = {
                "correct_rate": correct / total if total else 0,
                "partial_rate": partial / total if total else 0,
                "failed_rate": (total - correct - partial) / total if total else 0,
                "score_distribution": {
                    "correct": correct,
                    "partial": partial,
                    "failed": total - correct - partial,
                },
            }

        token_counts = [r.total_tokens for r in valid_runs]
        cost_per_1k = _estimate_cost_per_1k(backend_name, float(np.mean(token_counts)))

        summary[backend_name] = {
            "num_valid_runs": len(valid_runs),
            "avg_latency_ms": float(np.mean(overall_latency_values)),
            "std_latency_ms": float(np.std(overall_latency_values)),
            "avg_latency_per_turn": avg_latency_per_turn,
            "recall_accuracy_by_seed_turn": recall_accuracy_by_seed,
            "avg_tokens_per_run": float(np.mean(token_counts)),
            "std_tokens_per_run": float(np.std(token_counts)),
            "estimated_cost_per_1k_conversations_usd": cost_per_1k,
        }

    return summary


def _estimate_cost_per_1k(backend_name: str, avg_tokens: float) -> float:
    """Rough cost estimate using gpt-3.5-turbo pricing as baseline."""
    # $0.002 per 1K tokens (blended input+output approximation for gpt-3.5-turbo)
    rate_per_token = 0.002 / 1000
    return avg_tokens * rate_per_token * 1000


def save_results(results: dict, results_dir: str = None) -> Path:
    results_dir = Path(results_dir or config.RESULTS_DIR)
    results_dir.mkdir(parents=True, exist_ok=True)

    timestamp = int(time.time())
    output_path = results_dir / f"benchmark_{timestamp}.json"

    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    logger.info("Results saved to %s", output_path)
    return output_path
