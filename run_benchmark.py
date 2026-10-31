#!/usr/bin/env python3
"""Entry point for the Agent Memory Showdown benchmark.

Usage:
    python run_benchmark.py                               # all backends, paid LLM
    python run_benchmark.py --backends buffer summary     # subset
    python run_benchmark.py --runs 3 --turns 50
    python run_benchmark.py --k 2 4 8                     # retrieval-depth sweep
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
from src.bundle import validate_label  # noqa: E402
from src.config import config  # noqa: E402
from src.dataset import parse_composition  # noqa: E402
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
    parser.add_argument("--facts", default=None, metavar="CATEGORY=N,...",
                        help="Facts per category, e.g. extraction=3,update=2,abstention=1 "
                             "(default: FACTS_PER_CATEGORY or "
                             f"{','.join(f'{c}={n}' for c, n in config.FACTS_PER_CATEGORY.items())})")
    parser.add_argument("--no-distractors", action="store_true",
                        help="Leave out distractor turns")
    parser.add_argument("--k", type=int, nargs="+", default=None, metavar="K",
                        help="Retrieval depth for top-k backends (default: RETRIEVAL_K="
                             f"{config.RETRIEVAL_K}). Several values run a sweep: "
                             "each top-k backend is reported once per k as name@kK")
    parser.add_argument("--results-dir", default=config.RESULTS_DIR,
                        help=f"Directory to write results (default: {config.RESULTS_DIR})")
    parser.add_argument("--label", default=None, type=_label,
                        help="Suffix for the run id (letters, digits, '.', '_', '-')")
    parser.add_argument("--no-viz", action="store_true", help="Skip generating visualizations")
    parser.add_argument("--no-judge", action="store_true",
                        help="Score with the deterministic matcher only (no judge LLM calls)")
    return parser.parse_args(argv)


def _label(value: str) -> str:
    try:
        return validate_label(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


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
        composition=parse_composition(args.facts) if args.facts else None,
        distractors=False if args.no_distractors else None,
        results_dir=args.results_dir,
        run_label=args.label,
        judge=False if args.no_judge else None,
        ks=args.k,
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
