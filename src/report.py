"""Plain-text summary of an aggregate, printed by run_benchmark and rescore."""

from __future__ import annotations


def _pct(x: float | None) -> str:
    return "  n/a" if x is None else f"{x * 100:5.1f}%"


def _ci(ci: list[float] | None) -> str:
    return "[no interval]" if ci is None else f"[{ci[0] * 100:.0f}-{ci[1] * 100:.0f}]"


def format_summary(aggregate: dict) -> str:
    lines = ["", "=== BENCHMARK SUMMARY ===", ""]
    if aggregate.get("is_sample"):
        lines.append("SAMPLE RUN (fake LLM): numbers below are not benchmark results.")
        lines.append("")
    scoring = aggregate.get("scoring") or {}
    if scoring.get("judge_model"):
        lines.append(f"Scored by judge {scoring['judge_model']} (matcher shown alongside).")
    else:
        lines.append("Scored by the deterministic matcher (no judge).")
    lines.append("Recall = mean of per-run correct rates with a 95% t interval over runs; "
                 "the per-probe rate's Wilson interval is approximate (probes in a run are not independent).")
    excluded = (aggregate.get("headline") or {}).get("excludes_categories") or []
    if excluded:
        lines.append(f"Headline recall leaves out: {', '.join(excluded)} (shown separately).")
    seeds = aggregate.get("seeds") or {}
    if seeds.get("dropped"):
        lines.append(f"WARNING: backends compared on paired runs {seeds['runs']} only; dropped "
                     + "; ".join(f"{b} runs {r}" for b, r in seeds["dropped"].items())
                     + " (they failed for another backend).")
    elif seeds and not seeds.get("paired", True):
        lines.append("WARNING: no run completed for every backend; each backend uses its own valid "
                     "runs, so the backends are not compared on the same datasets.")
    lines.append("")
    for backend, data in aggregate["backends"].items():
        if "error" in data:
            lines.append(f"{backend:12s}  ERROR: {data['error']}")
            continue
        o = data["recall_overall"]
        rm = data["recall_run_mean"]
        line = (
            f"{backend:12s}  recall={_pct(rm['mean'])} {_ci(rm['ci95'])} (runs={rm['n']})  "
            f"per probe={_pct(o['correct_rate'])} ~{_ci(o['correct_ci95'])} (n={o['n']})  "
            f"partial={o['counts']['partial']} wrong={o['counts']['wrong']} "
            f"refused={o['counts']['refused']} abstained={o['counts']['abstained']}"
        )
        if data.get("agreement"):
            line += f"  matcher={_pct(data['matcher']['recall_overall']['correct_rate'])}"
        lines.append(line)
        lat = data["latency"]
        lines.append(
            f"{'':12s}  latency p50/p95 ms: retrieve {lat['retrieve_ms']['p50']:.1f}/"
            f"{lat['retrieve_ms']['p95']:.1f}  llm {lat['llm_ms']['p50']:.1f}/{lat['llm_ms']['p95']:.1f}"
            f"  write {lat['write_ms']['p50']:.1f}/{lat['write_ms']['p95']:.1f}"
        )
        tok = data["tokens"]
        cost = data.get("cost")
        cost_txt = "unpriced model"
        if cost:
            per_correct = cost["per_correct_recall_usd"]
            cost_txt = (
                f"${cost['per_conversation_usd']:.4f}/conversation "
                f"(${cost['per_1k_conversations_usd']:.2f} per 1K), "
                f"per correct recall "
                f"{'n/a' if per_correct is None else f'${per_correct:.4f}'}"
            )
        mem = tok["memory"]
        extra = (f", memory writes {mem['calls']:.0f} calls / {mem['input_tokens'] + mem['output_tokens']:.0f} tok"
                 if mem["calls"] else "")
        lines.append(
            f"{'':12s}  tokens/conversation in={tok['input_tokens']:.0f} out={tok['output_tokens']:.0f}"
            f"{extra}  cost {cost_txt}"
        )
        cats = data.get("recall_by_category") or {}
        if cats:
            lines.append(f"{'':12s}  by category: " + "  ".join(
                f"{c} {_pct(d['correct_rate']).strip()} (n={d['n']})" for c, d in cats.items()
            ))
        abst = data.get("recall_abstention")
        if abst:
            lines.append(
                f"{'':12s}  abstention (not in headline): says it was not told "
                f"{_pct(abst['correct_rate']).strip()} (n={abst['n']})"
            )
        sens = data.get("recall_sensitive")
        if sens:
            lines.append(
                f"{'':12s}  sensitive (not in headline): correct {_pct(sens['correct_rate']).strip()}"
                f" refused {_pct(sens['refused_rate']).strip()} (n={sens['n']})"
            )
        size = data.get("memory_size_end")
        if size:
            lines.append(f"{'':12s}  memory at end: {size['mean']:.0f} {size['unit']}")
        for cp, entry in data["recall_by_checkpoint"].items():
            lines.append(
                f"{'':12s}    checkpoint {cp:>3s}: {_pct(entry['correct_rate'])} "
                f"{_ci(entry['correct_ci95'])} (n={entry['n']})"
            )
    agreement = aggregate.get("agreement")
    if agreement and agreement["n"]:
        kappa = agreement["kappa"]
        lines.append("")
        lines.append(
            f"Matcher/judge agreement: {agreement['observed'] * 100:.1f}% observed, "
            f"kappa={'n/a' if kappa is None else f'{kappa:.3f}'}, "
            f"{agreement['disagreements']} disagreement(s) listed in aggregate.json"
        )
    lines.append("")
    return "\n".join(lines)
