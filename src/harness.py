"""Benchmark harness: runs backends through the dataset and probes at checkpoints.

Conversation turns go through `backend.chat` (retrieve, answer, write). After a
checkpoint turn, every fact planted so far is asked through `backend.probe`
(retrieve, answer, no write) in a seeded random order. The memory fingerprint is
taken before and after the probes; if it changed, the run is aborted, because
the measurement would be contaminated.
"""

from __future__ import annotations

import logging
import random
import time
from pathlib import Path
from typing import Type

from src.backends.base import BaseMemoryBackend, backend_label
from src.bundle import (
    BundleWriter,
    environment_info,
    git_info,
    new_run_id,
    package_versions,
    utc_now,
)
from src.config import config
from src.dataset import NON_HEADLINE, ConversationDataset, generate_dataset, load_bank
from src.llm_factory import embedding_model_id, llm_model_id
from src.prompts import CHAT_TEMPLATE, template_hash

logger = logging.getLogger(__name__)


class ProbeIsolationError(RuntimeError):
    """A probe changed the memory it was supposed to only read."""


def run_single(
    backend_cls: Type[BaseMemoryBackend],
    dataset: ConversationDataset,
    run_index: int,
    writer: BundleWriter,
    backend_kwargs: dict | None = None,
    sweep: bool = False,
) -> dict:
    backend = backend_cls(**(backend_kwargs or {}))
    base = {"backend": backend.label(sweep), "run_index": run_index}
    writer.record(
        {**base, "type": "run_start", "seed": dataset.seed, "session_id": backend.session_id,
         "k": getattr(backend, "k", None), "started_at": utc_now()}
    )
    facts_by_id = {f.id: f for f in dataset.facts}
    checkpoints = set(dataset.checkpoints)
    started = time.perf_counter()
    error = None
    memory_stats = None
    try:
        backend.setup()
        for turn in dataset.turns:
            exchange = backend.chat(turn.human_message)
            writer.record(
                {**base, "type": "turn", "turn": turn.turn_number, "fact_id": turn.fact_id,
                 **exchange.to_dict()}
            )
            if turn.turn_number in checkpoints:
                _run_checkpoint(backend, dataset, turn.turn_number, writer, base, facts_by_id)
        memory_stats = backend.memory_stats()
    except Exception as exc:  # recorded in the bundle; other runs continue
        logger.error("Backend %s run %d failed: %s", base["backend"], run_index, exc, exc_info=True)
        error = f"{type(exc).__name__}: {exc}"
    finally:
        teardown_error = None
        try:
            backend.teardown()
        except Exception as exc:
            logger.warning("Teardown of %s run %d failed: %s", base["backend"], run_index, exc)
            teardown_error = f"{type(exc).__name__}: {exc}"
    end = {
        **base, "type": "run_end", "error": error, "teardown_error": teardown_error,
        "duration_s": time.perf_counter() - started, "memory_stats": memory_stats,
        "finished_at": utc_now(),
    }
    writer.record(end)
    return end


def _run_checkpoint(backend, dataset, checkpoint, writer, base, facts_by_id) -> None:
    facts = dataset.probes_at(checkpoint)
    rng = random.Random(f"{dataset.seed}:{checkpoint}")
    order = [f.id for f in facts]
    rng.shuffle(order)
    before = backend.memory_fingerprint()
    for position, fact_id in enumerate(order):
        fact = facts_by_id[fact_id]
        exchange = backend.probe(fact.probe)
        writer.record(
            {**base, "type": "probe", "checkpoint": checkpoint, "order": position,
             "fact_id": fact.id, "category": fact.category, "headline": fact.headline,
             "planted_at": fact.turn if fact.statements else None, "question": fact.probe,
             "answer_key": fact.answer_key, "answers": fact.answers, "stale": fact.stale,
             **exchange.to_dict()}
        )
    after = backend.memory_fingerprint()
    unchanged = before == after
    writer.record(
        {**base, "type": "checkpoint", "checkpoint": checkpoint, "num_probes": len(order),
         "memory_before": before, "memory_after": after, "unchanged": unchanged}
    )
    if not unchanged:
        raise ProbeIsolationError(
            f"{base['backend']}: memory changed during checkpoint {checkpoint}: {before} -> {after}"
        )


def build_manifest(backend_names, num_runs, num_turns, dataset_info, checkpoints, k) -> dict:
    return {
        "methodology": "v2",
        "created_at": utc_now(),
        "git": git_info(),
        "llm_provider": config.LLM_PROVIDER,
        "llm_model": llm_model_id(),
        "embedding_provider": config.EMBEDDING_PROVIDER,
        "embedding_model": embedding_model_id(),
        "embedding_dimension": config.EMBEDDING_DIMENSION,
        # An int, or the list of k values when the run is a k sweep.
        "k": k,
        "backends": list(backend_names),
        "num_runs": num_runs,
        "num_turns": num_turns,
        "dataset": dataset_info,
        "checkpoints": list(checkpoints),
        "seeds": [config.BASE_SEED + i for i in range(num_runs)],
        "prompt_hash": template_hash(),
        "prompt_template": CHAT_TEMPLATE,
        "packages": package_versions(),
        "environment": environment_info(),
        # Any fake component (chat model, judge or embeddings) makes the numbers a sample.
        "is_sample": is_sample_config(),
    }


def is_sample_config() -> bool:
    return "fake" in (config.LLM_PROVIDER, config.JUDGE_PROVIDER, config.EMBEDDING_PROVIDER)


def run_benchmark(
    backend_classes: list[Type[BaseMemoryBackend]],
    num_runs: int | None = None,
    num_turns: int | None = None,
    checkpoints: list[int] | None = None,
    composition: dict[str, int] | None = None,
    distractors: bool | None = None,
    results_dir: str | Path | None = None,
    run_label: str | None = None,
    backend_kwargs: dict | None = None,
    judge: bool | None = None,
    ks: list[int] | None = None,
) -> Path:
    """Run the benchmark and write a bundle. Returns the bundle directory.

    After the conversations, every probe is scored by the deterministic matcher
    and (unless `judge` is False, or JUDGE=0) by the LLM judge; the labels go to
    `scores.jsonl` and the judge settings into the manifest.

    `ks` sweeps the retrieval depth: with more than one value, every backend
    that retrieves top-k (`uses_k`) runs once per k and is reported as
    `name@k<k>`; backends that ignore k run once. A single value just sets k.
    """
    from src.aggregate import aggregate_bundle
    from src.bundle import read_transcript
    from src.scoring.rescore import score_probes, scoring_info, write_jsonl

    use_judge = config.JUDGE_ENABLED if judge is None else judge

    num_runs = num_runs or config.NUM_RUNS
    num_turns = num_turns or config.NUM_TURNS
    composition = composition if composition is not None else config.FACTS_PER_CATEGORY
    distractors = config.DISTRACTORS if distractors is None else distractors
    checkpoints = checkpoints if checkpoints is not None else config.CHECKPOINTS
    backend_kwargs = dict(backend_kwargs or {})
    if ks:
        ks = list(dict.fromkeys(int(v) for v in ks))
        if any(v < 1 for v in ks):
            raise ValueError(f"k values must be positive, got {ks}")
        if len(ks) == 1:
            backend_kwargs["k"] = ks[0]
    sweep = bool(ks) and len(ks) > 1
    k = backend_kwargs.get("k", config.RETRIEVAL_K)
    plan = []  # (label, backend class, kwargs)
    for cls in backend_classes:
        for value in (ks if sweep and cls.uses_k else [k]):
            plan.append((backend_label(cls, value, sweep), cls, {**backend_kwargs, "k": value}))
    runs_root = Path(results_dir or config.RESULTS_DIR) / "runs"

    bank = load_bank()
    datasets = [
        generate_dataset(num_turns=num_turns, checkpoints=checkpoints, random_seed=config.BASE_SEED + i,
                         composition=composition, distractors=distractors, bank=bank)
        for i in range(num_runs)
    ]
    dataset_info = {
        "bank": str(Path(bank.path).relative_to(Path(__file__).resolve().parents[1])),
        "bank_version": bank.version,
        "bank_sha256": bank.sha256,
        "composition": dict(composition),
        "distractors": bool(distractors),
        "headline_excludes": sorted(NON_HEADLINE),
    }
    manifest = build_manifest(
        [label for label, _, _ in plan], num_runs, num_turns, dataset_info,
        datasets[0].checkpoints if datasets else checkpoints, ks if sweep else k,
    )
    writer = BundleWriter(runs_root, new_run_id(run_label), manifest)
    writer.write_dataset({str(i): d.to_dict() for i, d in enumerate(datasets)})

    started = time.perf_counter()
    for label, backend_cls, kwargs in plan:
        logger.info("Benchmarking backend: %s", label)
        for run_idx, dataset in enumerate(datasets):
            logger.info("  Run %d / %d", run_idx + 1, num_runs)
            run_single(backend_cls, dataset, run_idx, writer, kwargs, sweep)

    duration = time.perf_counter() - started
    judge_obj = None
    if use_judge:
        from src.scoring.judge import get_judge

        judge_obj = get_judge()
    writer.close_transcript()
    scores = score_probes(read_transcript(writer.path), judge_obj)
    info = scoring_info(judge_obj)
    write_jsonl(writer.path / "scores.jsonl", scores)
    writer.write_json("scoring.json", info)
    writer.finalize(finished_at=utc_now(), duration_s=duration, scoring=info)
    writer.write_aggregate(aggregate_bundle(writer.path))
    logger.info("Run bundle written to %s", writer.path)
    return writer.path
