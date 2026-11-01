#!/usr/bin/env python3
"""Does the model repeat sensitive facts (passwords, PINs) that are in its context?

Uses the benchmark's own dataset: for each seed it generates the conversation
from data/facts_v2.yaml with only `sensitive` facts planted (plus the usual
filler), puts the whole conversation in context the way the `buffer` backend
does, renders the shared chat prompt, and asks each sensitive probe. Responses
are labelled by the same matcher as the benchmark, so `refused` is reported
separately from `correct`.

This is what the `sensitive` category in the benchmark measures, run on its
own. It calls the configured LLM (LLM_PROVIDER, default `do`, which is paid
and needs DO_API_KEY). With LLM_PROVIDER=fake it runs offline.

    python scripts/test_sensitive_recall.py --seeds 5
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.backends.base import format_exchange  # noqa: E402
from src.dataset import generate_dataset, load_bank  # noqa: E402
from src.prompts import render_chat_prompt  # noqa: E402
from src.scoring.matcher import match_record  # noqa: E402

ACK = "Got it."


def history_for(dataset) -> str:
    """Every turn of the conversation as the buffer backend would hold it."""
    return "\n".join(format_exchange(t.human_message, ACK) for t in dataset.turns)


def run(seeds: int, base_seed: int, turns: int, llm=None) -> dict:
    if llm is None:
        from src.llm_factory import get_llm

        llm = get_llm()
    count = len(load_bank().by_category("sensitive"))
    labels: Counter = Counter()
    rows = []
    for i in range(seeds):
        dataset = generate_dataset(
            num_turns=turns, checkpoints=[turns], random_seed=base_seed + i,
            composition={"sensitive": count}, distractors=False,
        )
        history = history_for(dataset)
        for fact in dataset.facts:
            response = llm.invoke(render_chat_prompt(history, fact.probe)).content
            label, _ = match_record({
                "response": response, "answers": fact.answers, "stale": fact.stale,
                "answer_key": fact.answer_key, "category": fact.category,
            })
            labels[label] += 1
            rows.append({"seed": base_seed + i, "fact_id": fact.id, "label": label,
                         "response": response})
    return {"labels": dict(labels), "rows": rows}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--seeds", type=int, default=5, help="conversations to generate (default 5)")
    parser.add_argument("--base-seed", type=int, default=42)
    parser.add_argument("--turns", type=int, default=50)
    args = parser.parse_args(argv)

    result = run(args.seeds, args.base_seed, args.turns)
    for row in result["rows"]:
        print(f"seed {row['seed']}  {row['fact_id']:14s}  {row['label']:9s}  "
              f"{row['response'].strip()[:120]!r}")
    total = sum(result["labels"].values())
    print()
    for label, n in sorted(result["labels"].items()):
        print(f"{label:9s} {n}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
