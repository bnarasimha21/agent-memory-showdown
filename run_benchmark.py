#!/usr/bin/env python3
"""Entry point for the Agent Memory Showdown benchmark.

Usage:
    python run_benchmark.py                               # all backends, paid LLM
    python run_benchmark.py --backends buffer summary     # subset
    python run_benchmark.py --runs 3 --turns 50
    LLM_PROVIDER=fake EMBEDDING_PROVIDER=fake python run_benchmark.py   # free, offline

Each invocation writes a run bundle to results/runs/<run_id>/.

Docker:
    make run
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("benchmark")

sys.path.insert(0, str(Path(__file__).parent))

from src.backends.registry import AVAILABLE_BACKENDS  # noqa: E402
from src.config import config  # noqa: E402
from src.harness import run_benchmark  # noqa: E402
from src.report import format_summary  # noqa: E402,F401  (re-exported)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Agent Memory Showdown - memory backend benchmark"
    )
    parser.add_argument(
        "--backends",
        nargs="+",
        choices=list(AVAILABLE_BACKENDS.keys()),
        default=list(AVAILABLE_BACKENDS.keys()),
        help="Which backends to benchmark (default: all)",
    )
    parser.add_argument("--runs", type=int, default=config.NUM_RUNS,
                        help=f"Number of runs per backend (default: {config.NUM_RUNS})")
    parser.add_argument("--turns", type=int, default=config.NUM_TURNS,
                        help=f"Conversation turns per run (default: {config.NUM_TURNS})")
    parser.add_argument("--checkpoints", type=int, nargs="+", default=None,
                        help=f"Probe after these turns (default: {config.CHECKPOINTS})")
    parser.add_argument("--results-dir", default=config.RESULTS_DIR,
                        help=f"Directory to write results (default: {config.RESULTS_DIR})")
    parser.add_argument("--label", default=None, help="Suffix for the run id")
    parser.add_argument("--no-viz", action="store_true", help="Skip generating visualizations")
    parser.add_argument("--no-judge", action="store_true",
                        help="Score with the deterministic matcher only (no judge LLM calls)")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    backend_classes = [AVAILABLE_BACKENDS[b] for b in args.backends]

    logger.info(
        "Starting benchmark: %d backend(s), %d runs, %d turns, LLM_PROVIDER=%s",
        len(backend_classes), args.runs, args.turns, config.LLM_PROVIDER,
    )

    bundle = run_benchmark(
        backend_classes=backend_classes,
        num_runs=args.runs,
        num_turns=args.turns,
        checkpoints=args.checkpoints,
        results_dir=args.results_dir,
        run_label=args.label,
        judge=False if args.no_judge else None,
    )
    aggregate_path = bundle / "aggregate.json"
    logger.info("Benchmark complete. Bundle: %s", bundle)

    if not args.no_viz:
        from src.visualize import generate_all

        generate_all(aggregate_path, bundle / "charts")

    import json

    print(format_summary(json.loads(aggregate_path.read_text())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
