"""Benchmark harness: runs backends through the dataset and probes at checkpoints.

Conversation turns go through `backend.chat` (retrieve, answer, write). After a
checkpoint turn, every fact planted so far is asked through `backend.probe`
(retrieve, answer, no write) in a seeded random order. The memory fingerprint is
taken before and after the probes; if it changed, the run is aborted, because
the measurement would be contaminated.
"""

from __future__ import annotations

import json
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
from src.llm_factory import embedding_model_id, llm_model_id, provider_caveats
from src.prompts import CHAT_TEMPLATE, template_hash
from src.retry import USAGE_LIMIT_PAUSES

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
             # Never-told facts: values a model might wrongly offer (the tempting
             # distractor among them); naming one makes the answer wrong.
             "candidates": sorted({str(v) for v in fact.values.values()}) if fact.expect_abstention else [],
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


def build_manifest(backend_names, num_runs, num_turns, dataset_info, checkpoints, k,
                   judge: bool = True) -> dict:
    return {
        "methodology": "v2",
        "created_at": utc_now(),
        "git": git_info(),
        "llm_provider": config.LLM_PROVIDER,
        "llm_model": llm_model_id(),
        "judge_provider": config.JUDGE_PROVIDER if judge else None,
        "provider_caveats": provider_caveats(judge),
        "embedding_provider": config.EMBEDDING_PROVIDER,
        "embedding_model": embedding_model_id(),
        "embedding_dimension": config.EMBEDDING_DIMENSION,
        # An int, the list of k values when the run is a k sweep, or None when
        # no backend in the run retrieves top-k.
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
        # Any fake component that took part (chat model, embeddings, or the
        # judge when judging is on) makes the numbers a sample.
        "is_sample": is_sample_config(judge),
    }


def _counters(duration_s, prior_calls, prior_pauses, calls_before, pauses_before) -> dict:
    """Manifest fields that accumulate over invocations: wall time, claude CLI calls, limit pauses."""
    out = {"duration_s": duration_s}
    if "claude_cli" in (config.LLM_PROVIDER, config.JUDGE_PROVIDER):
        out["claude_cli_calls"] = prior_calls + _cli_calls() - calls_before
    pauses = prior_pauses + USAGE_LIMIT_PAUSES[pauses_before:]
    if pauses:
        out["usage_limit_pauses"] = pauses
    return out


def _cli_calls() -> int:
    import sys

    module = sys.modules.get("src.claude_cli")
    return module.CALLS if module else 0


def _check_resumable(old: dict, new: dict, path: Path, datasets) -> None:
    """Refuse to resume into a bundle the current configuration would not have produced."""
    for key in ("backends", "num_runs", "num_turns", "checkpoints", "seeds", "k", "dataset",
                "prompt_hash", "llm_provider", "llm_model", "embedding_provider", "embedding_model",
                "embedding_dimension", "judge_provider"):
        if old.get(key) != new.get(key):
            raise ValueError(f"cannot resume {path}: {key} differs (bundle {old.get(key)!r}, "
                             f"now {new.get(key)!r})")
    saved = json.loads((path / "dataset.json").read_text(encoding="utf-8"))
    if saved != json.loads(json.dumps({str(i): d.to_dict() for i, d in enumerate(datasets)})):
        raise ValueError(f"cannot resume {path}: the datasets it was run on are not the ones "
                         "this configuration generates")


def is_sample_config(judge: bool = True) -> bool:
    """A fake JUDGE_PROVIDER only matters when the judge runs (not under --no-judge)."""
    providers = [config.LLM_PROVIDER, config.EMBEDDING_PROVIDER] + ([config.JUDGE_PROVIDER] if judge else [])
    return "fake" in providers


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
    resume: str | Path | None = None,
) -> Path:
    """Run the benchmark and write a bundle. Returns the bundle directory.

    After the conversations, every probe is scored by the deterministic matcher
    and (unless `judge` is False, or JUDGE=0) by the LLM judge; the labels go to
    `scores.jsonl` and the judge settings into the manifest.

    `resume` continues an unfinished bundle (a path, or a run id under the
    results directory): runs that finished are kept, runs that did not (or that
    failed) are dropped from the transcript and run again, and judge verdicts
    already made are reused. The configuration must match the bundle's
    manifest and regenerate the same datasets, otherwise it is refused.

    `ks` sweeps the retrieval depth: with more than one value, every backend
    that retrieves top-k (`uses_k`) runs once per k and is reported as
    `name@k<k>`; backends that ignore k run once. A single value just sets k.
    """
    from src.aggregate import aggregate_bundle
    from src.bundle import read_transcript
    from src.scoring.rescore import JudgeCache, score_probes, scoring_info, write_jsonl

    use_judge = config.JUDGE_ENABLED if judge is None else judge
    # Calls and usage-limit pauses are counted from here, so two benchmarks in
    # one process (a resume in a test, say) do not count each other's.
    calls_before, pauses_before = _cli_calls(), len(USAGE_LIMIT_PAUSES)

    num_runs = config.NUM_RUNS if num_runs is None else num_runs
    num_turns = config.NUM_TURNS if num_turns is None else num_turns
    if num_runs < 1:
        raise ValueError(f"runs must be at least 1, got {num_runs}")
    if num_turns < 1:
        raise ValueError(f"turns must be at least 1, got {num_turns}")
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
    # A sweep only happens when some backend uses k; otherwise every backend
    # runs once and the manifest must not claim several k values were run.
    any_k = any(cls.uses_k for cls in backend_classes)
    sweep = bool(ks) and len(ks) > 1 and any_k
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
    headline_probes = sum(n for d in datasets for c, n in d.expected_probe_counts().items()
                          if c not in NON_HEADLINE)
    if headline_probes == 0:
        raise ValueError(
            "this configuration asks no headline probe (no non-abstention, non-sensitive fact is "
            f"ready by a checkpoint: composition {dict(composition)}, checkpoints {checkpoints}, "
            f"{num_turns} turns), so there would be no recall to report")

    # Load the embedding model before any paid work too: with a missing package
    # or model every vector backend would fail run after run, after the
    # buffer and summary conversations had already been paid for.
    if any_k:
        from src.llm_factory import get_embeddings

        try:
            get_embeddings().embed_query("preflight")
        except Exception as exc:
            raise RuntimeError(f"the embedding model ({embedding_model_id()}) cannot be loaded, so the "
                               f"vector backends cannot run: {exc}") from exc

    # Resolve the judge before any paid work, so a bad judge setting fails now
    # rather than after every conversation has been paid for.
    judge_obj = None
    if use_judge:
        from src.scoring.judge import get_judge

        judge_obj = get_judge()

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
        datasets[0].checkpoints if datasets else checkpoints, (ks if sweep else k) if any_k else None,
        judge=bool(use_judge),
    )
    prior_s, prior_calls, prior_pauses = 0.0, 0, []
    done: set[tuple[str, int]] = set()
    if resume:
        bundle_dir = Path(resume)
        if not bundle_dir.exists():
            bundle_dir = runs_root / str(resume)
        writer = BundleWriter.reopen(bundle_dir)
        _check_resumable(writer.manifest, manifest, bundle_dir, datasets)
        old = read_transcript(writer.path)
        done = {(r["backend"], r["run_index"]) for r in old
                if r["type"] == "run_end" and r.get("error") is None}
        started_keys = {(r["backend"], r["run_index"]) for r in old if r["type"] == "run_start"}
        dropped = writer.drop_runs(started_keys - done)
        logger.info("RESUMING %s: %d run(s) already finished, %d unfinished or failed run(s) "
                    "dropped (%d records) and rerun", writer.run_id, len(done),
                    len(started_keys - done), dropped)
        prior_s = float(writer.manifest.get("duration_s") or 0.0)
        prior_calls = int(writer.manifest.get("claude_cli_calls") or 0)
        prior_pauses = list(writer.manifest.get("usage_limit_pauses") or [])
        writer.manifest.setdefault("resumed_at", []).append(utc_now())
        writer.write_json("manifest.json", writer.manifest)
    else:
        writer = BundleWriter(runs_root, new_run_id(run_label), manifest)
        writer.write_dataset({str(i): d.to_dict() for i, d in enumerate(datasets)})

    started = time.perf_counter()
    for label, backend_cls, kwargs in plan:
        logger.info("Benchmarking backend: %s", label)
        for run_idx, dataset in enumerate(datasets):
            if (label, run_idx) in done:
                logger.info("  Run %d / %d already finished, skipped", run_idx + 1, num_runs)
                continue
            logger.info("  Run %d / %d", run_idx + 1, num_runs)
            run_single(backend_cls, dataset, run_idx, writer, kwargs, sweep)
            # Totals so far, so a killed process still leaves honest counters for a resume.
            writer.manifest.update(_counters(prior_s + time.perf_counter() - started, prior_calls,
                                             prior_pauses, calls_before, pauses_before))
            writer.write_json("manifest.json", writer.manifest)

    duration = prior_s + time.perf_counter() - started
    writer.close_transcript()
    cache = JudgeCache(writer.path / "judge_cache.jsonl", judge_obj) if judge_obj is not None else None
    scores = score_probes(read_transcript(writer.path), judge_obj, cache)
    info = scoring_info(judge_obj)
    write_jsonl(writer.path / "scores.jsonl", scores)
    writer.write_json("scoring.json", info)
    extra = _counters(duration, prior_calls, prior_pauses, calls_before, pauses_before)
    writer.finalize(finished_at=utc_now(), scoring=info, **extra)
    writer.write_aggregate(aggregate_bundle(writer.path))
    logger.info("Run bundle written to %s", writer.path)
    return writer.path
