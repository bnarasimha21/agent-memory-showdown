"""Generate docs/GUIDE.md, "Which memory, when, at what cost", from a run bundle.

    python -m src.site.guide                          # headline bundle of results/latest.json -> docs/GUIDE.md
    python -m src.site.guide results/runs/<run_id>    # preview another bundle on stdout
    python -m src.site.guide results/runs/<run_id> --out FILE

Every figure in the guide is read from the bundle's `aggregate.json` (recall
and its intervals, cost, latency, recall by category) or derived from those
figures by the rules in `picks`. The run's settings (runs, turns, model ids)
come from its `manifest.json`. Nothing is typed in by hand, so the guide for a
sample bundle says at the top that it is a sample, and its "pick this when"
section is labelled as rule output on sample data.

The committed guide belongs to the headline bundle: `python -m src.site.export`
and `python -m src.site.publish` regenerate it, and `export --check` fails when
it is stale.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from src.report import provider_note
from src.site.data import REPO_ROOT, Bundle, load_bundle, published_bundles, seed_pairing, self_judged

GUIDE = REPO_ROOT / "docs" / "GUIDE.md"
TITLE = "Which memory, when, at what cost"
# Categories the "pick this when" section names a winner for, with the question each answers.
CATEGORY_QUESTIONS = {
    "extraction": "single facts stated once",
    "update": "facts that are corrected later",
    "temporal": "date arithmetic across turns",
    "multi_hop": "combining two facts from different turns",
    "abstention": "saying so when the user never told it (highest rate means it makes things up least)",
}
EPS = 1e-12


def _fmt():
    from src.site import export  # export imports this module too

    return export


def _family(label: str) -> tuple[str, int | None]:
    """("qdrant", 2) for "qdrant@k2"; ("buffer", None) for a backend without k."""
    match = re.fullmatch(r"(.+)@k(\d+)", label)
    return (match[1], int(match[2])) if match else (label, None)


def rows(bundle: Bundle) -> dict[str, dict]:
    """Per backend label, the aggregate figures the guide uses. Failed backends keep only `error`."""
    out = {}
    for label, data in bundle.backends.items():
        if "error" in data:
            out[label] = {"error": data["error"]}
            continue
        run_mean = data.get("recall_run_mean") or {}
        overall = data.get("recall_overall") or {}
        cost = data.get("cost") or {}
        latency = data.get("latency") or {}
        retrieve, write, llm = (latency.get(c) or {} for c in ("retrieve_ms", "write_ms", "llm_ms"))
        memory_p50 = (None if retrieve.get("p50") is None or write.get("p50") is None
                      else retrieve["p50"] + write["p50"])
        out[label] = {
            "error": None,
            "recall": run_mean.get("mean"),
            "ci": run_mean.get("ci95"),
            "ci_method": run_mean.get("method"),
            "runs": run_mean.get("n"),
            "probe_recall": overall.get("correct_rate"),
            "probe_ci": overall.get("correct_ci95"),
            "probes": overall.get("n", 0),
            "cost_conv": cost.get("per_conversation_usd"),
            "cost_conv_ci": cost.get("per_conversation_ci95"),
            "cost_1k": cost.get("per_1k_conversations_usd"),
            "cost_memory": cost.get("memory_maintenance_per_conversation_usd"),
            "cost_correct": cost.get("per_correct_recall_usd"),
            "tokens": (data.get("tokens") or {}).get("total_tokens"),
            "retrieve": retrieve, "write": write, "llm": llm,
            "memory_p50": memory_p50,
            "categories": data.get("recall_by_category") or {},
        }
    return out


def _overlaps(a, b) -> bool:
    return a is not None and b is not None and a[0] <= b[1] + EPS and b[0] <= a[1] + EPS


def _lowest(candidates: dict[str, dict], key: str) -> list[str]:
    """Labels with the lowest value of `key` (ties kept), ignoring missing values."""
    have = {label: r[key] for label, r in candidates.items() if r.get(key) is not None}
    if not have:
        return []
    low = min(have.values())
    return [label for label, v in have.items() if v <= low + EPS]


def picks(bundle: Bundle) -> dict:
    """The rule outputs behind "pick this when", all derived from the aggregate.

    - `best`: label(s) with the highest run-mean recall.
    - `contenders`: labels whose 95% interval overlaps the best one's. They are
      not separated from the best by this run. `behind` is everyone else.
      With one run there are no intervals: `separable` is False and only the
      best label(s) are contenders.
    - `cheapest`: contender(s) with the lowest cost per conversation.
    - `cheapest_per_correct`: label(s) with the lowest cost per correct recall, over all backends.
    - `fastest`: contender(s) with the lowest memory time (read p50 + write p50).
    - `by_category`: per category, the label(s) with the highest correct rate, and that rate.
    - `k`: per swept backend, the best k and the smallest k whose interval overlaps it.
    """
    ok = {label: r for label, r in rows(bundle).items() if not r["error"] and r["recall"] is not None}
    if not ok:
        return {}
    top = max(r["recall"] for r in ok.values())
    best = [label for label, r in ok.items() if r["recall"] >= top - EPS]
    separable = all(r["ci"] is not None for r in ok.values())
    if separable:
        best_ci = (min(ok[b]["ci"][0] for b in best), max(ok[b]["ci"][1] for b in best))
        contenders = [label for label, r in ok.items() if _overlaps(r["ci"], best_ci)]
    else:
        contenders = list(best)
    pool = {label: ok[label] for label in contenders}

    by_category = {}
    for category in CATEGORY_QUESTIONS:
        rates = {label: r["categories"][category] for label, r in ok.items()
                 if category in r["categories"] and r["categories"][category].get("n")}
        if rates:
            high = max(d["correct_rate"] for d in rates.values())
            by_category[category] = {
                "labels": [label for label, d in rates.items() if d["correct_rate"] >= high - EPS],
                "rate": high, "all_tied": all(d["correct_rate"] >= high - EPS for d in rates.values()),
                "n": max(d["n"] for d in rates.values()),
            }

    families: dict[str, dict[int, str]] = {}
    for label in ok:
        family, k = _family(label)
        if k is not None:
            families.setdefault(family, {})[k] = label
    k_picks = {}
    for family, by_k in families.items():
        if len(by_k) < 2:
            continue
        best_k = max(sorted(by_k), key=lambda k: ok[by_k[k]]["recall"])  # smallest k on a tie
        enough = (min(k for k in by_k if _overlaps(ok[by_k[k]]["ci"], ok[by_k[best_k]]["ci"]))
                  if separable else None)
        k_picks[family] = {"best_k": best_k, "smallest_overlapping_k": enough, "labels": by_k}

    return {
        "rows": ok, "best": best, "separable": separable, "contenders": contenders,
        "behind": [label for label in ok if label not in contenders],
        "cheapest": _lowest(pool, "cost_conv"),
        "cheapest_per_correct": _lowest(ok, "cost_correct"),
        "fastest": _lowest(pool, "memory_p50"),
        "by_category": by_category, "k": k_picks,
    }


# ------------------------------------------------------------------ rendering


def _names(labels: list[str]) -> str:
    return ", ".join(f"`{label}`" for label in labels) if labels else "none"


def _recall(r: dict) -> str:
    f = _fmt()
    return f"{f.pct(r['recall'])} {f.ci(r['ci'])}"


def _banner(bundle: Bundle) -> list[str]:
    m, scoring = bundle.manifest, bundle.aggregate.get("scoring") or {}
    lines = []
    if bundle.is_sample:
        lines += [
            "> **SAMPLE DATA. THIS IS NOT A BENCHMARK RESULT AND NOT A RECOMMENDATION.**",
            f"> This guide was generated from `{bundle.run_id}`, a sample run in which at least one of "
            f"the chat model, the judge and the embeddings was fake (`LLM_PROVIDER={m.get('llm_provider')}`, "
            f"`JUDGE_PROVIDER={scoring.get('judge_provider') or 'none'}`, "
            f"`EMBEDDING_PROVIDER={m.get('embedding_provider')}`). The fake model can only copy from its "
            "prompt, so every number below describes the harness and the format of this guide. None of "
            "them says anything about a real model or a real memory backend, and the costs are what the "
            "recorded fake tokens would cost at the listed price. Do not quote them. The guide is "
            "regenerated from a real run when one is published (`make run-v2`, then `make publish`).",
            "",
        ]
    elif self_judged(bundle):
        lines += [
            f"> **Caveat: the judge was the answering model** (`{scoring.get('judge_model')}`). A model "
            "may favour its own answers, so recall here may be too high. The matcher figures in "
            "`aggregate.json` are the check on that.",
            "",
        ]
    note = provider_note(m.get("provider_caveats"))
    if note:
        lines += [f"> **Provider note.** {note}", ""]
    pairing = seed_pairing(bundle)
    if pairing and pairing["warning"]:
        lines += [f"> **WARNING:** {pairing['warning']}", ""]
    return lines


def _run_facts(bundle: Bundle, link: str) -> list[str]:
    f = _fmt()
    m, a = bundle.manifest, bundle.aggregate
    scoring, pricing = a.get("scoring") or {}, a.get("pricing") or {}
    judge = (f"judge `{scoring['judge_model']}`" if scoring.get("judge_model")
             else "scored by the deterministic matcher only (no judge)")
    if pricing.get("unpriced"):
        price = f"The model `{pricing.get('model')}` has no entry in `pricing.yaml`, so no cost is shown."
    else:
        price = (f"Cost is recorded tokens at {f.usd(pricing.get('input_per_mtok'))} per million input "
                 f"tokens and {f.usd(pricing.get('output_per_mtok'))} per million output tokens "
                 f"(`{pricing.get('model')}`, source: {pricing.get('source')}, checked "
                 f"{pricing.get('checked_on')}). List price, no prompt caching discount.")
    return [
        f"Source: [`aggregate.json`]({link}/aggregate.json) and [`manifest.json`]({link}/manifest.json) "
        f"of run `{bundle.run_id}`. {m.get('num_runs')} runs of {m.get('num_turns')} turns, checkpoints "
        f"{', '.join(str(c) for c in m.get('checkpoints', []))}, answering model `{m.get('llm_model')}`, "
        f"{judge}, embeddings `{m.get('embedding_model')}`, k = {f.k_text(m.get('k'))}. {price}",
        "",
        "How to read the figures:",
        "",
        "- **Recall** is the mean of per-run recall with a 95% Student t interval over runs. It leaves "
        "out the `abstention` and `sensitive` categories, which are shown on their own under recall by "
        "category. With few runs the interval is wide. Two backends whose intervals overlap are not "
        "separated by this run; that is not the same as being equal.",
        "- **Cost per conversation** covers the answering calls and memory upkeep (summary rewrites, "
        "fact extraction). **Cost per correct recall** is conversation spend plus headline probe spend, "
        "divided by the headline probes answered correctly.",
        "- **Memory latency** is the time the memory itself adds to a turn: the read before the answer "
        "and the write after it. For `summary` and `mem0` the write includes an LLM call.",
        "",
    ]


def _recall_table(data: dict[str, dict]) -> list[str]:
    f = _fmt()
    lines = ["| Backend | Recall, run mean [95% CI] | Runs | Per probe [approx. Wilson] | Probes |",
             "|---------|--------------------------:|-----:|---------------------------:|-------:|"]
    for label, r in data.items():
        if r["error"]:
            lines.append(f"| {label} | failed: {r['error']} | | | |")
            continue
        pooled = " (runs identical: pooled Wilson)" if r["ci_method"] == "wilson-pooled" else ""
        lines.append(f"| {label} | {_recall(r)}{pooled} | {f.fmt(r['runs'], 'd')} | "
                     f"{f.pct(r['probe_recall'])} {f.ci(r['probe_ci'])} | {r['probes']} |")
    return lines


def _cost_table(data: dict[str, dict]) -> list[str]:
    f = _fmt()
    lines = ["| Backend | Cost / conversation [bootstrap 95% CI] | Cost / 1K conversations | Of which memory upkeep "
             "/ conversation | Cost / correct recall | Tokens / conversation |",
             "|---------|---------------------------------------:|------------------------:|-----------------------"
             "---------------:|----------------------:|----------------------:|"]
    for label, r in data.items():
        if r["error"]:
            continue
        ci = (f" [{f.usd(r['cost_conv_ci'][0], 4)}, {f.usd(r['cost_conv_ci'][1], 4)}]"
              if r["cost_conv_ci"] else "")
        lines.append(f"| {label} | {f.usd(r['cost_conv'], 4)}{ci} | {f.usd(r['cost_1k'])} | "
                     f"{f.usd(r['cost_memory'], 4)} | {f.usd(r['cost_correct'], 4)} | {f.fmt(r['tokens'])} |")
    return lines


def _latency_table(data: dict[str, dict]) -> list[str]:
    f = _fmt()
    lines = ["| Backend | Memory read p50 / p95 | Memory write p50 / p95 | Answering call p50 / p95 |",
             "|---------|----------------------:|-----------------------:|-------------------------:|"]
    for label, r in data.items():
        if r["error"]:
            continue
        cells = [f"{f.ms(r[c].get('p50'))} / {f.ms(r[c].get('p95'))} ms" for c in ("retrieve", "write", "llm")]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    return lines


def _category_table(data: dict[str, dict]) -> list[str]:
    f = _fmt()
    categories: list[str] = []
    for r in data.values():
        categories += [c for c in (r.get("categories") or {}) if c not in categories]
    if not categories:
        return ["No probe was scored."]
    lines = ["| Backend | " + " | ".join(categories) + " |",
             "|---------|" + "|".join("---:" for _ in categories) + "|"]
    for label, r in data.items():
        if r["error"]:
            continue
        cells = []
        for c in categories:
            d = r["categories"].get(c)
            cells.append("n/a" if not d or not d.get("n") else
                         f"{f.pct(d['correct_rate'], 0)} {f.ci(d['correct_ci95'])} (n={d['n']})")
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    return lines


def _pick_lines(bundle: Bundle) -> list[str]:
    f = _fmt()
    p = picks(bundle)
    if not p:
        return ["No backend finished a run, so there is nothing to pick from."]
    ok = p["rows"]
    lines = []
    best = p["best"][0]
    lines.append(f"- **Highest recall:** {_names(p['best'])} at {_recall(ok[best])}.")
    if not p["separable"]:
        lines.append("- **One run only, so there are no intervals.** This bundle cannot say which "
                     "differences between backends are real. The picks below compare point values.")
    elif p["behind"]:
        lines.append(
            f"- **Not separated from the best:** {_names(p['contenders'])}. Their recall intervals "
            f"overlap the best one's. **Behind the best:** {_names(p['behind'])}, whose intervals lie "
            "entirely below it.")
    else:
        lines.append(
            "- **This run does not separate any backend from the best on recall:** every interval "
            "overlaps the best one's. On this evidence the choice comes down to cost and latency; more "
            "runs would be needed to rank recall.")
    if p["cheapest"]:
        pick = p["cheapest"][0]
        text = (f"- **Pick {_names(p['cheapest'])} when you want the cheapest backend whose recall is "
                f"not separated from the best:** {f.usd(ok[pick]['cost_conv'], 4)} per conversation at "
                f"{_recall(ok[pick])} recall.")
        if pick not in p["best"] and ok[best]["cost_conv"] and ok[pick]["cost_conv"]:
            text += (f" The highest-recall backend, `{best}`, costs {f.usd(ok[best]['cost_conv'], 4)} per "
                     f"conversation, {ok[best]['cost_conv'] / ok[pick]['cost_conv']:.1f} times as much.")
        lines.append(text)
    if p["cheapest_per_correct"]:
        pick = p["cheapest_per_correct"][0]
        lines.append(f"- **Pick {_names(p['cheapest_per_correct'])} when the unit you pay for is a correct "
                     f"answer:** {f.usd(ok[pick]['cost_correct'], 4)} per correct recall, the lowest of "
                     f"all backends, at {_recall(ok[pick])} recall.")
    if p["fastest"]:
        pick = p["fastest"][0]
        lines.append(
            f"- **Pick {_names(p['fastest'])} when the memory must add the least time to a turn** (among "
            f"the backends not separated from the best): {f.ms(ok[pick]['retrieve'].get('p50'))} ms read "
            f"plus {f.ms(ok[pick]['write'].get('p50'))} ms write at p50. Compare that with the answering "
            f"call's p50 of {f.ms(ok[pick]['llm'].get('p50'))} ms before treating it as a reason.")
    for category, question in CATEGORY_QUESTIONS.items():
        c = p["by_category"].get(category)
        if not c:
            continue
        if c["all_tied"]:
            lines.append(f"- **For {question}** (`{category}`): every backend scored {f.pct(c['rate'], 0)}, "
                         f"so this category does not tell them apart (up to {c['n']} probes each).")
        else:
            others = [label for label in ok if label not in c["labels"]
                      and (ok[label]["categories"].get(category) or {}).get("n")]
            who = (_names(c["labels"]) if len(c["labels"]) <= 3 else
                   f"{len(c['labels'])} backends tied (all except {_names(others)}) and")
            lines.append(f"- **For {question}** (`{category}`): {who} scored highest, "
                         f"{f.pct(c['rate'], 0)} (up to {c['n']} probes each; see the table for the "
                         "intervals, which are wide).")
    for family, k in p["k"].items():
        best_label = k["labels"][k["best_k"]]
        if k["smallest_overlapping_k"] is None:
            lines.append(f"- **Retrieval depth for `{family}`:** k = {k['best_k']} had the highest recall "
                         f"({f.pct(ok[best_label]['recall'])}); with one run there is no interval to "
                         "compare the other depths against.")
            continue
        small = k["labels"][k["smallest_overlapping_k"]]
        text = (f"- **Retrieval depth for `{family}`:** k = {k['best_k']} had the highest recall "
                f"({_recall(ok[best_label])}).")
        if small != best_label:
            text += (f" k = {k['smallest_overlapping_k']} is the smallest depth not separated from it "
                     f"({_recall(ok[small])}) at {f.usd(ok[small]['cost_conv'], 4)} per conversation "
                     f"against {f.usd(ok[best_label]['cost_conv'], 4)}.")
        elif k["best_k"] == min(k["labels"]):
            text += " It is the smallest depth swept, and no larger depth scored higher."
        else:
            text += " No smaller depth has an interval that overlaps it."
        lines.append(text)
    return lines


def render(bundle: Bundle, guide_path: Path = GUIDE) -> str:
    """The guide for one bundle, as Markdown."""
    link = Path(_relative(bundle.path, guide_path.parent)).as_posix()
    data = rows(bundle)
    sample = bundle.is_sample
    lines = [
        f"<!-- GENERATED by `python -m src.site.guide` from run {bundle.run_id}; do not edit by hand. -->",
        "",
        f"# {TITLE}" + (" (sample data, not a result)" if sample else ""),
        "",
        *_banner(bundle),
        *_run_facts(bundle, link),
        "## Pick this when" + (" (rule output on sample data, not advice)" if sample else ""),
        "",
    ]
    if sample:
        lines += ["The lines below show what the rules print. They were computed from fake-model numbers "
                  "and are not advice about any backend.", ""]
    lines += [
        "Each line is produced by a fixed rule in `src/site/guide.py` from the tables that follow. The "
        "rules compare 95% intervals, so they say \"not separated\" far more often than \"better\".",
        "",
        *[line.replace("- ", "- (sample) ", 1) if sample else line for line in _pick_lines(bundle)],
        "",
        "## Recall",
        "",
        *_recall_table(data),
        "",
        "## Cost",
        "",
        *_cost_table(data),
        "",
        "## Memory-layer latency",
        "",
        *_latency_table(data),
        "",
        "## Recall by category",
        "",
        "Correct rate over probes with an approximate 95% Wilson interval (probes in one run share a "
        "memory, so the true interval is wider). `abstention` and `sensitive` are not part of headline "
        "recall.",
        "",
        *_category_table(data),
        "",
        "## What this guide does not cover",
        "",
        "It reports one run configuration: one answering model, one embedding model, synthetic "
        "conversations of the length given above, and a single user. The design record "
        "([DESIGN.md](DESIGN.md), sections 6 and 7) lists what that leaves open.",
        "",
    ]
    return "\n".join(lines)


def _relative(path: Path, start: Path) -> str:
    import os

    return os.path.relpath(path.resolve(), start.resolve())


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("bundle", nargs="?", default=None,
                        help="results/runs/<run_id> (default: the headline bundle of results/latest.json)")
    parser.add_argument("--out", default=None,
                        help="file to write (default: docs/GUIDE.md for the headline bundle, stdout for "
                             "a bundle given on the command line)")
    args = parser.parse_args(argv)
    if args.bundle is None:
        bundle, out = published_bundles()[0], Path(args.out) if args.out else GUIDE
    else:
        bundle, out = load_bundle(args.bundle), Path(args.out) if args.out else None
    if out is None:
        sys.stdout.write(render(bundle))
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(bundle, out), encoding="utf-8")
    print(f"wrote {out} from {bundle.run_id}" + (" (SAMPLE, not a result)" if bundle.is_sample else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
