"""Memory-side latency of each backend, with no paid model calls.

Runs the real harness (real Qdrant, real Postgres, the real local embedding
model) with the offline fake chat model and no judge, then prints the time
each backend spends reading memory before a turn (`retrieve_ms`) and storing
the exchange after it (`write_ms`). The answering model is left out on
purpose: this measures the memory layer only, which is the part a backend
choice changes and the part that is the same whatever model answers.

Usage (services up, `make up`):

    python scripts/memory_latency.py                 # 5 runs x 50 turns
    python scripts/memory_latency.py --runs 2 --turns 30

What it does not measure:

- The answering call. With the fake model `llm_ms` is near zero.
- `summary` and `mem0` writes. Their write is an LLM call (the summary
  rewrite, mem0's fact extraction), so with the fake model it times the fake.
  They are printed with that marked, and left out of `--backends` by default.
- Realistic stored text. The fake model's replies are shorter than a real
  model's, so each stored exchange is shorter and embeds a little faster.

The bundle it writes is a sample (fake chat model) and goes to a temporary
directory, never to `results/`.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

LLM_WRITES = {"summary", "mem0"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--backends", nargs="+",
                        default=["buffer", "qdrant", "pgvector", "langgraph_store"])
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--turns", type=int, default=50)
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument("--json", action="store_true", help="print the figures as JSON")
    args = parser.parse_args()

    os.environ["LLM_PROVIDER"] = "fake"
    os.environ["JUDGE_PROVIDER"] = "fake"
    os.environ["JUDGE"] = "0"
    os.environ.setdefault("EMBEDDING_PROVIDER", "local")

    from src.config import config

    config.reload()
    from src.aggregate import aggregate_bundle
    from src.backends.registry import AVAILABLE_BACKENDS
    from src.harness import run_benchmark

    checkpoints = [t for t in config.CHECKPOINTS if t <= args.turns] or [args.turns]
    with tempfile.TemporaryDirectory(prefix="ams-latency-") as tmp:
        bundle = run_benchmark([AVAILABLE_BACKENDS[b] for b in args.backends], num_runs=args.runs,
                               num_turns=args.turns, checkpoints=checkpoints, results_dir=tmp,
                               run_label="memory-latency", judge=False, ks=[args.k])
        agg = aggregate_bundle(bundle)
        manifest = json.loads((Path(bundle) / "manifest.json").read_text(encoding="utf-8"))

    rows = {}
    for name, b in agg["backends"].items():
        lat = b["latency"]
        rows[name] = {
            "valid_runs": b["num_valid_runs"],
            "turns_timed": lat["retrieve_ms"]["n"],
            "retrieve_p50_ms": lat["retrieve_ms"]["p50"],
            "retrieve_p95_ms": lat["retrieve_ms"]["p95"],
            "write_p50_ms": lat["write_ms"]["p50"],
            "write_p95_ms": lat["write_ms"]["p95"],
            "write_is_llm_call": name.split("@")[0] in LLM_WRITES,
        }
    out = {
        "runs": args.runs, "turns": args.turns, "k": args.k,
        "embedding_model": manifest.get("embedding_model"),
        "packages": manifest.get("packages"),
        "python": platform.python_version(),
        "machine": f"{platform.machine()}, {os.cpu_count()} CPUs",
        "backends": rows,
    }
    if args.json:
        print(json.dumps(out, indent=2))
        return 0
    print(f"{args.runs} runs x {args.turns} turns, k = {args.k}, embeddings "
          f"{out['embedding_model']}, Python {out['python']}, {out['machine']}")
    print(f"{'backend':<18}{'turns':>7}{'read p50':>11}{'read p95':>11}{'write p50':>11}{'write p95':>11}")
    for name, r in rows.items():
        mark = "  (write is an LLM call: fake model timed)" if r["write_is_llm_call"] else ""
        print(f"{name:<18}{r['turns_timed']:>7}{r['retrieve_p50_ms']:>9.2f}ms{r['retrieve_p95_ms']:>9.2f}ms"
              f"{r['write_p50_ms']:>9.2f}ms{r['write_p95_ms']:>9.2f}ms{mark}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
