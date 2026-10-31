"""Generate the README results block and the video's data file from committed data.

    python -m src.site.export           # rewrite both
    python -m src.site.export --check   # exit 1, with a diff, if either is stale (CI)

Sources: `results/legacy/v1_published.json` (the v1 numbers, the only record of
that run) and the bundles listed in `results/latest.json`.

- README.md: everything between the BEGIN/END GENERATED RESULTS markers.
- remotion/src/data/benchmarkData.ts: the v1 constants the video narrates,
  unchanged in value, plus `LATEST_RUN`, a summary of the headline v2 bundle.
  The video keeps the v1 numbers until a real (non-sample) v2 run replaces
  the narration; `LATEST_RUN.isSample` says whether the v2 numbers are real.
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path

from src.site.data import (
    LATEST, LEGACY_V1, PAGES_URL, REPO_ROOT, RUNS_DIR, Bundle, headline_row, load_legacy,
    published_bundles, seed_pairing,
)

README = REPO_ROOT / "README.md"
BENCHMARK_DATA_TS = REPO_ROOT / "remotion" / "src" / "data" / "benchmarkData.ts"
BEGIN = "<!-- BEGIN GENERATED RESULTS: python -m src.site.export, do not edit by hand -->"
END = "<!-- END GENERATED RESULTS -->"


def pct(x: float | None, digits: int = 1) -> str:
    return "n/a" if x is None else f"{x * 100:.{digits}f}%"


def ci(pair) -> str:
    return "n/a" if not pair else f"[{pair[0] * 100:.0f}, {pair[1] * 100:.0f}]"


def usd(x: float | None, digits: int = 2) -> str:
    return "n/a" if x is None else f"${x:,.{digits}f}"


def fmt(x, spec: str = ",.0f", suffix: str = "") -> str:
    """A number with a format spec, or "n/a" when the aggregate has none."""
    return "n/a" if x is None else format(x, spec) + suffix


def _round(x, digits: int = 1):
    return None if x is None else round(x, digits)


def k_text(k) -> str:
    if k is None:
        return "n/a"
    return ", ".join(str(v) for v in k) if isinstance(k, list) else str(k)


def ms(x: float | None) -> str:
    """Milliseconds: whole numbers from 10 ms up, one decimal below (fake runs are sub-ms)."""
    if x is None:
        return "n/a"
    return f"{x:,.0f}" if x >= 10 else f"{x:.1f}"


def _rel(path: Path) -> str:
    """Repo-relative path for links; a path outside the repo is shown as it is."""
    path = path.resolve()
    return path.relative_to(REPO_ROOT).as_posix() if path.is_relative_to(REPO_ROOT) else path.as_posix()


# --------------------------------------------------------------------- README


def v2_markdown(bundle: Bundle, headline: bool = True) -> list[str]:
    m = bundle.manifest
    src = _rel(bundle.path)
    title = "Latest v2 run" if headline else "Earlier v2 run"
    lines = [f"### {title}: `{bundle.run_id}`", ""]
    if bundle.is_sample:
        lines += [
            "> **Sample run, not a benchmark result.** At least one of the chat model, the judge and "
            f"the embeddings was fake (`LLM_PROVIDER={m.get('llm_provider')}`, "
            f"`JUDGE_PROVIDER={(bundle.aggregate.get('scoring') or {}).get('judge_provider') or 'none'}`, "
            f"`EMBEDDING_PROVIDER={m.get('embedding_provider')}`). It shows the bundle format, the site "
            "and the charts. The numbers describe the harness, not any model or memory backend; costs "
            "are what the recorded token counts would cost at the listed price.",
            "",
        ]
    lines += [
        f"{m.get('num_runs')} runs x {m.get('num_turns')} turns, checkpoints "
        f"{', '.join(str(c) for c in m.get('checkpoints', []))}, model `{m.get('llm_model')}`, "
        f"embeddings `{m.get('embedding_model')}`, k = {k_text(m.get('k'))}. "
        f"Source: [`manifest.json`]({src}/manifest.json), [`aggregate.json`]({src}/aggregate.json). "
        f"Recall leaves out the `abstention` and `sensitive` categories (reported on their own on "
        f"the results site and in `aggregate.json`). Recall is the mean of per-run recall with a 95% "
        f"Student t interval over runs; the per-probe Wilson interval is approximate, since probes "
        f"in one run are not independent. " + agreement_text(bundle),
        "",
    ]
    pairing = seed_pairing(bundle)
    if pairing and pairing["warning"]:
        lines += [f"> **WARNING:** {pairing['warning']}", ""]
    if pairing and pairing["kind"] == "paired":
        lines += [pairing["text"], ""]
    lines += [
        "| Backend | Recall, run mean [95% t CI] | Per probe [approx. Wilson] | Probes in recall | Cost / 1K conv | Cost / correct recall "
        "| Latency p50 / p95 | Memory at end |",
        "|---------|----------------:|------------------:|-------:|---------------:|----------------------:"
        "|------------------:|--------------:|",
    ]
    for label, data in bundle.backends.items():
        r = headline_row(data)
        if r["error"]:
            lines.append(f"| {label} | failed: {r['error']} | | | | | | |")
            continue
        lines.append(
            f"| {label} | {pct(r['run_mean'])} {ci(r['run_mean_ci'])} | {pct(r['recall'])} "
            f"{ci(r['recall_ci'])} | {r['headline_n']} | {usd(r['cost_per_1k'])} | "
            f"{usd(r['cost_per_correct'], 4)} | {ms(r['latency_p50'])} / {ms(r['latency_p95'])} ms | "
            f"{fmt(r['memory_end'])} {r['memory_unit'] or ''} |"
        )
    return lines


def agreement_text(bundle: Bundle) -> str:
    scoring = bundle.aggregate.get("scoring") or {}
    agreement = bundle.aggregate.get("agreement") or {}
    if not scoring.get("judge_model"):
        return "Scored by the deterministic matcher only (no judge)."
    if scoring.get("judge_provider") == "fake":
        return (f"Judge `{scoring['judge_model']}` is the offline fake, which applies the matcher rules, "
                "so its agreement with the matcher says nothing about a real judge.")
    same = (" It is also the answering model, so it may favour its own answers (self-preference); "
            "the matcher figures in `aggregate.json` are the check on that."
            if scoring.get("judge_is_answering_model") else "")
    return (f"Judge `{scoring['judge_model']}`; matcher/judge agreement: Cohen's kappa "
            f"{fmt(agreement.get('kappa'), '.3f')} over {agreement.get('n', 0)} probes "
            "(every disagreement is listed in `aggregate.json`)." + same)


def v1_markdown(legacy: dict) -> list[str]:
    c = legacy["constants"]
    src = _rel(LEGACY_V1)
    lines = [
        "### v1 published numbers (v1 methodology, known limits)",
        "",
        f"From the {legacy['published']} run of the v1 harness (source: [`{Path(src).name}`]({src})). "
        "v1 had known flaws: " + " ".join(legacy["limitations"]) + " Treat these as indicative, "
        "not as a clean measurement, and not as comparable with v2.",
        "",
        "| Backend | Recall @ turn 15 | Recall @ turn 50 | Avg latency / turn | Cost / 1K convos | Tokens / run |",
        "|---------|:----------------:|:----------------:|:------------------:|:----------------:|:------------:|",
    ]
    for b in c["BACKENDS"]:
        lines.append(
            f"| {b} | {c['RECALL_AT_TURN_15'][b]}% | {c['RECALL_AT_TURN_50'][b]}% | "
            f"{c['AVG_LATENCY_MS'][b] / 1000:.1f}s | ${c['COST_PER_1K'][b]:,} | "
            f"{c['AVG_TOKENS'][b] / 1000:.0f}K |"
        )
    return lines


def readme_block(bundles: list[Bundle], legacy: dict) -> str:
    lines = [f"Interactive results, with every probe's transcript: <{PAGES_URL}>", ""]
    if bundles[0].is_sample:
        real = [b.run_id for b in bundles if not b.is_sample]
        lines += [("**No real v2 benchmark is published yet.** The headline bundle below is a sample "
                   "made offline; see *Setup* to make a real run (it needs `DO_API_KEY`) and "
                   "*Results site and publishing* to publish it.") if not real else
                  (f"**The headline bundle is a sample** although a real run is published "
                   f"(`{real[0]}`); republish the real run to make it the headline."), ""]
    for i, bundle in enumerate(bundles):
        lines += v2_markdown(bundle, headline=i == 0) + [""]
    lines += v1_markdown(legacy)
    return "\n".join(lines)


def render_readme(text: str, block: str) -> str:
    """Replace what is between the markers (the markers stay) with `block`."""
    start, end = text.find(BEGIN), text.find(END)
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"README.md must contain the markers\n{BEGIN}\n{END}")
    return text[:start] + f"{BEGIN}\n\n{block.strip()}\n\n{END}" + text[end + len(END):]


# ------------------------------------------------------------- benchmarkData.ts

# How each v1 constant is declared in TypeScript (the video relies on these types).
TS_DECL = {
    "BACKENDS": ("", " as const"),
    "BACKEND_LABELS": (": Record<Backend, string>", ""),
    "SEEDED_FACTS": ("", " as const"),
    "RECALL_AT_TURN_15": (": Record<Backend, number>", ""),
    "RECALL_AT_TURN_50": (": Record<Backend, number>", ""),
    "RECALL_BY_SEED_TURN_AT_50": (": Record<Backend, number[]>", ""),
    "SEED_TURNS": ("", ""),
    "AVG_LATENCY_MS": (": Record<Backend, number>", ""),
    "STD_LATENCY_MS": (": Record<Backend, number>", ""),
    "LATENCY_PER_TURN": (": Record<Backend, number[]>", ""),
    "AVG_TOKENS": (": Record<Backend, number>", ""),
    "COST_PER_1K": (": Record<Backend, number>", ""),
    "WALL_CLOCK": (": Record<Backend, string>", ""),
    "QDRANT_VS_PGVECTOR": ("", " as const"),
}


def _ts(value, indent: int = 0) -> str:
    """TypeScript literal: objects one key per line, scalars and flat arrays inline."""
    pad = "  " * indent
    if isinstance(value, dict):
        if all(not isinstance(v, (dict, list)) or _flat(v) for v in value.values()) and indent > 0:
            return "{ " + ", ".join(f"{_key(k)}: {_ts(v)}" for k, v in value.items()) + " }"
        inner = "".join(f"{pad}  {_key(k)}: {_ts(v, indent + 1)},\n" for k, v in value.items())
        return "{\n" + inner + pad + "}"
    if isinstance(value, list):
        if _flat(value):
            return "[" + ", ".join(_ts(v) for v in value) + "]"
        inner = "".join(f"{pad}  {_ts(v, indent + 1)},\n" for v in value)
        return "[\n" + inner + pad + "]"
    if isinstance(value, bool) or value is None:
        return json.dumps(value)
    if isinstance(value, float):
        return repr(round(value, 6))
    return json.dumps(value, ensure_ascii=False)


def _flat(v) -> bool:
    return isinstance(v, list) and all(not isinstance(x, (dict, list)) for x in v)


def _key(k: str) -> str:
    return k if k.isidentifier() else json.dumps(k)


def latest_run_summary(bundle: Bundle) -> dict:
    rows = []
    for label, data in bundle.backends.items():
        r = headline_row(data)
        if r["error"]:
            rows.append({"label": label, "error": r["error"]})
            continue
        rows.append({
            "label": label,
            # Headline: mean of per-run recall, 95% t interval over runs (None for one run).
            "recallPct": None if r["run_mean"] is None else round(r["run_mean"] * 100, 1),
            "recallCi95Pct": ([round(v * 100, 1) for v in r["run_mean_ci"]]
                              if r["run_mean_ci"] else None),
            "recallRuns": r["runs_used"],
            # Pooled over probes; the Wilson interval is approximate (probes in a run are not independent).
            "perProbeRecallPct": None if r["recall"] is None else round(r["recall"] * 100, 1),
            "perProbeApproxCi95Pct": [round(v * 100, 1) for v in r["recall_ci"]] if r["recall_ci"] else None,
            "recallProbes": r["headline_n"],
            "costPer1kUsd": _round(r["cost_per_1k"], 2),
            "latencyP50Ms": _round(r["latency_p50"], 1),
            "tokensPerConversation": _round(r["tokens"], None),
        })
    m = bundle.manifest
    return {
        "runId": bundle.run_id,
        "isSample": bundle.is_sample,
        "methodology": m.get("methodology", "v2"),
        "llmModel": m.get("llm_model"),
        "numRuns": m.get("num_runs"),
        "numTurns": m.get("num_turns"),
        "checkpoints": m.get("checkpoints", []),
        "backends": rows,
    }


def render_benchmark_data_ts(legacy: dict, headline: Bundle) -> str:
    c = legacy["constants"]
    if set(c) != set(TS_DECL):
        raise ValueError(f"v1 constants changed: {sorted(set(c) ^ set(TS_DECL))}")
    out = [
        "// GENERATED by `python -m src.site.export`; do not edit by hand.",
        f"// v1 constants: {_rel(LEGACY_V1)} (the {legacy['published']} v1 run, v1 methodology",
        "// with known limits, see the README). LATEST_RUN: the headline bundle in results/latest.json.",
        "",
    ]
    for name, (annotation, suffix) in TS_DECL.items():
        out.append(f"export const {name}{annotation} = {_ts(c[name])}{suffix};")
        if name == "BACKENDS":
            out.append("export type Backend = (typeof BACKENDS)[number];")
        out.append("")
    summary = latest_run_summary(headline)
    note = ("a SAMPLE run made with the fake LLM: not a benchmark result"
            if summary["isSample"] else "a real v2 run")
    out += [
        f"/** Headline v2 bundle, results/runs/{headline.run_id}: {note}. */",
        f"export const LATEST_RUN = {_ts(summary)} as const;",
        "",
    ]
    return "\n".join(out)


# ----------------------------------------------------------------------- main


def outputs_for(bundles: list[Bundle], readme_text: str | None = None) -> dict[Path, str]:
    """README and benchmarkData.ts as they should be for these bundles (headline first)."""
    legacy = load_legacy()
    text = README.read_text(encoding="utf-8") if readme_text is None else readme_text
    return {
        README: render_readme(text, readme_block(bundles, legacy)),
        BENCHMARK_DATA_TS: render_benchmark_data_ts(legacy, bundles[0]),
    }


def outputs(latest: Path = LATEST, runs_dir: Path = RUNS_DIR) -> dict[Path, str]:
    return outputs_for(published_bundles(latest, runs_dir))


def write_outputs(generated: dict[Path, str]) -> list[Path]:
    written = []
    for path, text in generated.items():
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            path.write_text(text, encoding="utf-8")
            written.append(path)
    return written


def stale(generated: dict[Path, str]) -> list[str]:
    diffs = []
    for path, text in generated.items():
        current = path.read_text(encoding="utf-8") if path.exists() else ""
        if current != text:
            diffs.append("".join(difflib.unified_diff(
                current.splitlines(keepends=True), text.splitlines(keepends=True),
                fromfile=f"{_rel(path)} (committed)", tofile=f"{_rel(path)} (generated)",
            )))
    return diffs


def write_all(latest: Path = LATEST, runs_dir: Path = RUNS_DIR) -> list[Path]:
    return write_outputs(outputs(latest, runs_dir))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate README results and benchmarkData.ts")
    parser.add_argument("--check", action="store_true",
                        help="do not write; exit 1 if the committed files differ from the generated ones")
    args = parser.parse_args(argv)
    if args.check:
        diffs = stale(outputs())
        for d in diffs:
            sys.stdout.write(d)
        if diffs:
            print("\nGenerated results are stale: run `python -m src.site.export` and commit.",
                  file=sys.stderr)
            return 1
        print("README results block and benchmarkData.ts are up to date.")
        return 0
    written = write_all()
    print("updated: " + (", ".join(_rel(p) for p in written) if written else "nothing (already current)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
