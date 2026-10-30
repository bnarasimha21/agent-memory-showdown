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
        extra = (f", summarizer {mem['calls']:.0f} calls / {mem['input_tokens'] + mem['output_tokens']:.0f} tok"
                 if mem["calls"] else "")
        lines.append(
            f"{'':12s}  tokens/conversation in={tok['input_tokens']:.0f} out={tok['output_tokens']:.0f}"
            f"{extra}  cost {cost_txt}"
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
