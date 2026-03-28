#!/usr/bin/env python3
"""Entry point for the Agent Memory Showdown benchmark.

Usage:
    python run_benchmark.py                     # run all backends
    python run_benchmark.py --backends buffer summary   # subset
    python run_benchmark.py --runs 3 --turns 50

Docker:
    make run
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("benchmark")

# Add project root to path when running outside Docker
sys.path.insert(0, str(Path(__file__).parent))

from src.config import config
from src.harness import run_benchmark, save_results
from src.visualize import generate_all
from src.backends.buffer_memory import BufferMemoryBackend
from src.backends.summary_memory import SummaryMemoryBackend
from src.backends.qdrant_memory import QdrantMemoryBackend
from src.backends.pgvector_memory import PGVectorMemoryBackend

AVAILABLE_BACKENDS = {
    "buffer": BufferMemoryBackend,
    "summary": SummaryMemoryBackend,
    "qdrant": QdrantMemoryBackend,
    "pgvector": PGVectorMemoryBackend,
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Agent Memory Showdown - LangChain memory backend benchmark"
    )
    parser.add_argument(
        "--backends",
        nargs="+",
        choices=list(AVAILABLE_BACKENDS.keys()),
        default=list(AVAILABLE_BACKENDS.keys()),
        help="Which backends to benchmark (default: all)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=config.NUM_RUNS,
        help=f"Number of runs per backend (default: {config.NUM_RUNS})",
    )
    parser.add_argument(
        "--turns",
        type=int,
        default=config.NUM_TURNS,
        help=f"Conversation turns per run (default: {config.NUM_TURNS})",
    )
    parser.add_argument(
        "--results-dir",
        default=config.RESULTS_DIR,
        help=f"Directory to write results (default: {config.RESULTS_DIR})",
    )
    parser.add_argument(
        "--no-viz",
        action="store_true",
        help="Skip generating visualizations",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    backend_classes = [AVAILABLE_BACKENDS[b] for b in args.backends]

    logger.info(
        "Starting benchmark: %d backend(s), %d runs, %d turns",
        len(backend_classes),
        args.runs,
        args.turns,
    )

    results = run_benchmark(
        backend_classes=backend_classes,
        num_runs=args.runs,
        num_turns=args.turns,
    )

    results_path = save_results(results, args.results_dir)
    logger.info("Benchmark complete. Results: %s", results_path)

    if not args.no_viz:
        viz_dir = Path(args.results_dir) / "charts"
        generate_all(results_path, viz_dir)

    # Print a quick summary table to stdout
    print("\n=== BENCHMARK SUMMARY ===\n")
    for backend, data in results.items():
        if "error" in data:
            print(f"{backend:12s}  ERROR: {data['error']}")
            continue
        avg_lat = data["avg_latency_ms"]
        std_lat = data["std_latency_ms"]
        recall_entries = data.get("recall_accuracy_by_seed_turn", {})
        if recall_entries:
            overall_correct = sum(
                v["correct_rate"] for v in recall_entries.values()
            ) / len(recall_entries)
        else:
            overall_correct = 0
        cost = data.get("estimated_cost_per_1k_conversations_usd", 0)
        print(
            f"{backend:12s}  "
            f"latency={avg_lat:7.1f}+/-{std_lat:5.1f}ms  "
            f"recall={overall_correct*100:5.1f}%  "
            f"cost/1K=${cost:.4f}"
        )

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
