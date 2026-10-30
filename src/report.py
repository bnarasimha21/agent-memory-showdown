"""Plain-text summary of an aggregate, printed by run_benchmark and rescore."""

from __future__ import annotations


def _pct(x: float) -> str:
    return f"{x * 100:5.1f}%"


def _ci(ci: list[float]) -> str:
    return f"[{ci[0] * 100:.0f}-{ci[1] * 100:.0f}]"


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
    lines.append("Recall = correct rate with 95% Wilson interval over probes; "
                 "run mean has a bootstrap interval over runs.")
    lines.append("")
    for backend, data in aggregate["backends"].items():
        if "error" in data:
            lines.append(f"{backend:12s}  ERROR: {data['error']}")
            continue
        o = data["recall_overall"]
        rm = data["recall_run_mean"]
        line = (
            f"{backend:12s}  recall={_pct(o['correct_rate'])} {_ci(o['correct_ci95'])} (n={o['n']})  "
            f"run mean={_pct(rm['mean'])} {_ci(rm['ci95'])}  "
            f"partial={o['counts']['partial']} wrong={o['counts']['wrong']} "
            f"refused={o['counts']['refused']} abstained={o['counts']['abstained']}"
        )
        if data.get("agreement"):
            line += f"  matcher={_pct(data['matcher']['recall_overall']['correct_rate'])}"
        lines.append(line)
        lines.append(
            f"{'':12s}  latency={data['avg_latency_ms']:.1f}+/-{data['std_latency_ms']:.1f}ms  "
            f"cost/1K=${data['estimated_cost_per_1k_conversations_usd']:.2f}"
        )
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
