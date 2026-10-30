"""Score (or re-score) the probe responses saved in a run bundle.

    python -m src.scoring.rescore results/runs/<run_id> [--out DIR] [--no-judge]

Reads `transcript.jsonl` and writes `scores.jsonl`, `scoring.json` and
`aggregate.json` to the output directory (default
`results/rescored/<run_id>-<timestamp>/`). The bundle itself is never modified,
so scoring can change without re-running the expensive conversation.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Iterable

from src.bundle import load_manifest, new_run_id, read_transcript, utc_now
from src.scoring.matcher import MATCHER_VERSION, match_record

logger = logging.getLogger(__name__)

SCORE_KEY = ("backend", "run_index", "checkpoint", "fact_id")


def score_key(record: dict) -> tuple:
    return tuple(record[k] for k in SCORE_KEY)


def score_probes(records: Iterable[dict], judge=None) -> list[dict]:
    """One score per probe record: matcher label always, judge label if a judge is given."""
    scores = []
    for rec in records:
        if rec.get("type") != "probe":
            continue
        label, reason = match_record(rec)
        score = {k: rec[k] for k in SCORE_KEY}
        score.update(
            matcher_label=label, matcher_reason=reason, judge_label=None,
            judge_rationale=None, judge_input_tokens=0, judge_output_tokens=0,
        )
        if judge is not None:
            verdict = judge.judge(rec)
            score.update(
                judge_label=verdict["label"], judge_rationale=verdict["rationale"],
                judge_input_tokens=verdict["input_tokens"],
                judge_output_tokens=verdict["output_tokens"],
            )
        scores.append(score)
    return scores


def scoring_info(judge=None) -> dict:
    info = {"matcher": MATCHER_VERSION, "scored_at": utc_now(), "judge_provider": None,
            "judge_model": None, "judge_prompt": None, "judge_prompt_hash": None}
    if judge is not None:
        info.update(judge.info())
    return info


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_scores(directory: str | Path) -> list[dict] | None:
    path = Path(directory) / "scores.jsonl"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_scoring_info(directory: str | Path) -> dict | None:
    path = Path(directory) / "scoring.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def score_into(bundle: str | Path, out_dir: str | Path, judge=None) -> dict:
    """Score a bundle's transcript and write scores + aggregate into `out_dir`."""
    from src.aggregate import aggregate_records

    bundle, out_dir = Path(bundle), Path(out_dir)
    records = read_transcript(bundle)
    manifest = load_manifest(bundle)
    scores = score_probes(records, judge)
    info = scoring_info(judge)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "scores.jsonl", scores)
    (out_dir / "scoring.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    aggregate = aggregate_records(records, manifest, scores=scores, scoring=info)
    (out_dir / "aggregate.json").write_text(
        json.dumps(aggregate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return aggregate


def rescore(bundle: str | Path, out_dir: str | Path | None = None, use_judge: bool = True,
            judge=None) -> tuple[Path, dict]:
    bundle = Path(bundle)
    if not (bundle / "transcript.jsonl").exists():
        raise FileNotFoundError(f"{bundle} has no transcript.jsonl")
    run_id = load_manifest(bundle).get("run_id", bundle.name)
    if out_dir is None:
        out_dir = bundle.parent.parent / "rescored" / f"{run_id}-{new_run_id()}"
    out_dir = Path(out_dir)
    if out_dir.resolve() == bundle.resolve() or bundle.resolve() in out_dir.resolve().parents:
        raise ValueError("rescore output must be outside the bundle; the bundle is never modified")
    if use_judge and judge is None:
        from src.scoring.judge import get_judge

        judge = get_judge()
    aggregate = score_into(bundle, out_dir, judge if use_judge else None)
    return out_dir, aggregate


def main(argv: list[str] | None = None) -> int:
    from src.report import format_summary

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Re-score a saved run bundle")
    parser.add_argument("bundle", help="results/runs/<run_id>")
    parser.add_argument("--out", default=None, help="output directory (outside the bundle)")
    parser.add_argument("--no-judge", action="store_true", help="matcher only, no LLM calls")
    args = parser.parse_args(argv)
    out_dir, aggregate = rescore(args.bundle, args.out, use_judge=not args.no_judge)
    print(format_summary(aggregate))
    print(f"Rescored aggregate written to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
