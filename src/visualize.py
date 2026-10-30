"""Generate visualization charts from benchmark results."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import plotly.graph_objects as go


BACKEND_COLORS = {
    "buffer": "#4C72B0",
    "summary": "#DD8452",
    "qdrant": "#55A868",
    "pgvector": "#C44E52",
}


def load_results(results_path: str | Path) -> dict:
    """Per-backend metrics from an aggregate.json written by src/aggregate.py."""
    with open(results_path) as f:
        return json.load(f)["backends"]


def _get_recall_curve_data(results: dict) -> dict:
    """Recall at each checkpoint for each backend (keys are checkpoint turns)."""
    curves = {}
    for backend, data in results.items():
        if "error" in data:
            continue
        by_cp = data.get("recall_by_checkpoint", {})
        turns = sorted(by_cp, key=int)
        curves[backend] = {
            "turns": [int(t) for t in turns],
            "correct_rates": [by_cp[t]["correct_rate"] for t in turns],
            "ci_low": [by_cp[t]["correct_ci95"][0] for t in turns],
            "ci_high": [by_cp[t]["correct_ci95"][1] for t in turns],
        }
    return curves


LABEL_COLORS = {
    "correct": "#55A868",
    "partial": "#CCB974",
    "wrong": "#C44E52",
    "refused": "#8172B2",
    "abstained": "#8C8C8C",
}


def _label_breakdown(results: dict) -> tuple[list[str], dict[str, list[float]]]:
    from src.scoring import LABELS

    backends = [b for b, d in results.items() if "error" not in d]
    rates = {lab: [results[b]["recall_overall"][f"{lab}_rate"] * 100 for b in backends]
             for lab in LABELS}
    return backends, rates


def plot_label_breakdown_plotly(results: dict, output_path: Path) -> None:
    backends, rates = _label_breakdown(results)
    fig = go.Figure()
    for label, values in rates.items():
        fig.add_trace(go.Bar(name=label, x=backends, y=values,
                             marker_color=LABEL_COLORS.get(label, "#888")))
    fig.update_layout(
        barmode="stack", title="Probe outcomes per backend (refusals separate from misses)",
        xaxis_title="Memory Backend", yaxis_title="Share of probes (%)",
        yaxis=dict(range=[0, 100]), template="plotly_white", width=800, height=450,
    )
    fig.write_html(str(output_path.with_suffix(".html")))
    try:
        fig.write_image(str(output_path.with_suffix(".png")))
    except Exception:
        pass


def plot_label_breakdown_matplotlib(results: dict, output_path: Path) -> None:
    backends, rates = _label_breakdown(results)
    fig, ax = plt.subplots(figsize=(8, 5))
    bottom = [0.0] * len(backends)
    for label, values in rates.items():
        ax.bar(backends, values, bottom=bottom, label=label,
               color=LABEL_COLORS.get(label, "#888"))
        bottom = [b + v for b, v in zip(bottom, values)]
    ax.set_title("Probe outcomes per backend (refusals separate from misses)")
    ax.set_ylabel("Share of probes (%)")
    ax.set_ylim(0, 100)
    ax.legend(loc="lower right", fontsize=8)
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=150)
    plt.close()


def _category_rows(results: dict) -> tuple[list[str], list[str], dict]:
    """(backends, categories, {backend: {category: dist}}) for recall_by_category."""
    from src.dataset import CATEGORIES

    backends = [b for b, d in results.items() if "error" not in d and d.get("recall_by_category")]
    present = {c for b in backends for c in results[b]["recall_by_category"]}
    categories = [c for c in CATEGORIES if c in present] + sorted(present - set(CATEGORIES))
    return backends, categories, {b: results[b]["recall_by_category"] for b in backends}


def plot_recall_by_category_matplotlib(results: dict, output_path: Path) -> None:
    """Grouped bars: correct rate per category per backend, with Wilson intervals.
    `sensitive` is drawn too but is not part of the headline number."""
    backends, categories, data = _category_rows(results)
    if not backends:
        return
    fig, ax = plt.subplots(figsize=(10, 5))
    width = 0.8 / len(backends)
    for i, backend in enumerate(backends):
        xs, ys, lo, hi = [], [], [], []
        for j, cat in enumerate(categories):
            d = data[backend].get(cat)
            if not d:
                continue
            rate = d["correct_rate"] * 100
            xs.append(j + i * width - 0.4 + width / 2)
            ys.append(rate)
            lo.append(rate - d["correct_ci95"][0] * 100)
            hi.append(d["correct_ci95"][1] * 100 - rate)
        ax.bar(xs, ys, width, yerr=[lo, hi], capsize=3, label=backend,
               color=BACKEND_COLORS.get(backend, "#888"))
    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels([c + (" *" if c == "sensitive" else "") for c in categories])
    ax.set_ylabel("Correct (%)")
    ax.set_ylim(0, 105)
    ax.set_title("Recall by fact category (* not in the headline number)")
    ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=150)
    plt.close()


def plot_recall_by_category_plotly(results: dict, output_path: Path) -> None:
    backends, categories, data = _category_rows(results)
    if not backends:
        return
    fig = go.Figure()
    for backend in backends:
        ys = [data[backend][c]["correct_rate"] * 100 if c in data[backend] else None
              for c in categories]
        fig.add_trace(go.Bar(name=backend, x=categories, y=ys,
                             marker_color=BACKEND_COLORS.get(backend, "#888")))
    fig.update_layout(
        barmode="group", title="Recall by fact category (sensitive is not in the headline number)",
        yaxis_title="Correct (%)", yaxis=dict(range=[0, 105]), template="plotly_white",
        width=900, height=450,
    )
    fig.write_html(str(output_path.with_suffix(".html")))
    try:
        fig.write_image(str(output_path.with_suffix(".png")))
    except Exception:
        pass


def plot_memory_decay_curve_plotly(results: dict, output_path: Path) -> None:
    curves = _get_recall_curve_data(results)
    fig = go.Figure()

    for backend, data in curves.items():
        color = BACKEND_COLORS.get(backend, "#888")
        fig.add_trace(
            go.Scatter(
                x=data["turns"],
                y=[r * 100 for r in data["correct_rates"]],
                mode="lines+markers",
                name=backend,
                error_y=dict(
                    type="data", symmetric=False,
                    array=[(h - r) * 100 for h, r in zip(data["ci_high"], data["correct_rates"])],
                    arrayminus=[(r - lo) * 100 for r, lo in zip(data["correct_rates"], data["ci_low"])],
                ),
                line=dict(color=color, width=2),
                marker=dict(size=8),
            )
        )

    fig.update_layout(
        title="Memory Decay Curve: Recall Accuracy by Checkpoint",
        xaxis_title="Checkpoint (after turn N)",
        yaxis_title="Recall Accuracy (%)",
        yaxis=dict(range=[0, 105]),
        legend_title="Backend",
        template="plotly_white",
        width=900,
        height=500,
    )
    fig.write_html(str(output_path.with_suffix(".html")))
    try:
        fig.write_image(str(output_path.with_suffix(".png")))
    except Exception:
        pass


def plot_memory_decay_curve_matplotlib(results: dict, output_path: Path) -> None:
    curves = _get_recall_curve_data(results)
    fig, ax = plt.subplots(figsize=(9, 5))

    for backend, data in curves.items():
        color = BACKEND_COLORS.get(backend, "#888")
        ax.errorbar(
            data["turns"],
            [r * 100 for r in data["correct_rates"]],
            yerr=[
                [(r - lo) * 100 for r, lo in zip(data["correct_rates"], data["ci_low"])],
                [(h - r) * 100 for h, r in zip(data["ci_high"], data["correct_rates"])],
            ],
            marker="o",
            color=color,
            linewidth=2,
            capsize=4,
            label=backend,
        )

    ax.set_title("Memory Decay Curve: Recall by Checkpoint (95% Wilson interval)")
    ax.set_xlabel("Checkpoint (after turn N)")
    ax.set_ylabel("Recall Accuracy (%)")
    ax.set_ylim(0, 105)
    ax.legend(title="Backend")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=150)
    plt.close()


COMPONENT_COLORS = {"retrieve_ms": "#4C72B0", "llm_ms": "#DD8452", "write_ms": "#55A868"}


def _latency_rows(results: dict) -> tuple[list[str], dict[str, dict[str, list[float]]]]:
    backends = [b for b, d in results.items() if "error" not in d]
    rows = {
        comp: {
            stat: [results[b]["latency"][comp][stat] for b in backends] for stat in ("p50", "p95")
        }
        for comp in COMPONENT_COLORS
    }
    return backends, rows


def plot_latency_bar_plotly(results: dict, output_path: Path) -> None:
    """p50 per component, stacked; the p95 of the total is drawn as a marker."""
    backends, rows = _latency_rows(results)
    fig = go.Figure()
    for comp, color in COMPONENT_COLORS.items():
        fig.add_trace(go.Bar(name=f"{comp} p50", x=backends, y=rows[comp]["p50"], marker_color=color))
    fig.add_trace(go.Scatter(
        name="total p95", x=backends, mode="markers",
        y=[results[b]["latency"]["total_ms"]["p95"] for b in backends],
        marker=dict(symbol="line-ew-open", size=30, color="#222"),
    ))
    fig.update_layout(
        barmode="stack", title="Latency per conversation turn (p50 by component, p95 total)",
        xaxis_title="Memory Backend", yaxis_title="Latency (ms)",
        template="plotly_white", width=800, height=450,
    )
    fig.write_html(str(output_path.with_suffix(".html")))
    try:
        fig.write_image(str(output_path.with_suffix(".png")))
    except Exception:
        pass


def plot_latency_bar_matplotlib(results: dict, output_path: Path) -> None:
    backends, rows = _latency_rows(results)
    fig, ax = plt.subplots(figsize=(8, 5))
    bottom = [0.0] * len(backends)
    for comp, color in COMPONENT_COLORS.items():
        ax.bar(backends, rows[comp]["p50"], bottom=bottom, color=color, label=f"{comp} p50")
        bottom = [b + v for b, v in zip(bottom, rows[comp]["p50"])]
    ax.scatter(backends, [results[b]["latency"]["total_ms"]["p95"] for b in backends],
               marker="_", s=600, color="#222", label="total p95", zorder=3)
    ax.set_title("Latency per conversation turn (p50 by component, p95 total)")
    ax.set_xlabel("Memory Backend")
    ax.set_ylabel("Latency (ms)")
    ax.legend(fontsize=8)
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=150)
    plt.close()


def plot_latency_by_turn_matplotlib(results: dict, output_path: Path) -> None:
    """One panel per latency component, one line per backend, x = turn."""
    backends = [b for b, d in results.items() if "error" not in d]
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.5), sharex=True)
    for ax, comp in zip(axes, COMPONENT_COLORS):
        for b in backends:
            by_turn = results[b]["latency_by_turn"]
            turns = sorted(by_turn, key=int)
            ax.plot([int(t) for t in turns], [by_turn[t][comp] for t in turns],
                    color=BACKEND_COLORS.get(b, "#888"), label=b, linewidth=1.5)
        ax.set_title(comp)
        ax.set_xlabel("Turn")
        ax.grid(True, alpha=0.3)
    axes[0].set_ylabel("Mean latency (ms)")
    axes[0].legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=150)
    plt.close()


def plot_latency_by_turn_plotly(results: dict, output_path: Path) -> None:
    from plotly.subplots import make_subplots

    backends = [b for b, d in results.items() if "error" not in d]
    comps = list(COMPONENT_COLORS)
    fig = make_subplots(rows=1, cols=3, subplot_titles=comps, shared_xaxes=True)
    for col, comp in enumerate(comps, start=1):
        for b in backends:
            by_turn = results[b]["latency_by_turn"]
            turns = sorted(by_turn, key=int)
            fig.add_trace(go.Scatter(
                x=[int(t) for t in turns], y=[by_turn[t][comp] for t in turns], mode="lines",
                name=b, legendgroup=b, showlegend=col == 1,
                line=dict(color=BACKEND_COLORS.get(b, "#888")),
            ), row=1, col=col)
    fig.update_layout(title="Latency by turn, per component (mean ms)", template="plotly_white",
                      width=1200, height=420)
    fig.write_html(str(output_path.with_suffix(".html")))
    try:
        fig.write_image(str(output_path.with_suffix(".png")))
    except Exception:
        pass


def build_cost_table(results: dict) -> str:
    """Markdown cost table computed from recorded tokens and pricing.yaml."""
    lines = [
        "| Backend | Input tok/conv | Output tok/conv | Summarizer calls/conv | Cost/conv (USD) "
        "| Cost/1K conv (USD) | Cost/correct recall (USD) |",
        "|---------|---------------:|----------------:|----------------------:|----------------:"
        "|-------------------:|--------------------------:|",
    ]
    for backend, data in results.items():
        if "error" in data:
            lines.append(f"| {backend} | ERROR | ERROR | ERROR | ERROR | ERROR | ERROR |")
            continue
        tok = data["tokens"]
        cost = data.get("cost")
        if cost:
            per_correct = cost["per_correct_recall_usd"]
            money = (f"${cost['per_conversation_usd']:.4f} | ${cost['per_1k_conversations_usd']:,.2f} | "
                     f"{'n/a' if per_correct is None else f'${per_correct:.4f}'}")
        else:
            money = "unpriced | unpriced | unpriced"
        lines.append(
            f"| {backend} | {tok['input_tokens']:,.0f} | {tok['output_tokens']:,.0f} | "
            f"{tok['memory']['calls']:.0f} | {money} |"
        )
    return "\n".join(lines)


def generate_all(results_path: str | Path, out_dir: str | Path) -> None:
    results_path = Path(results_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    results = load_results(results_path)

    plot_memory_decay_curve_plotly(results, out_dir / "memory_decay_curve")
    plot_memory_decay_curve_matplotlib(results, out_dir / "memory_decay_curve.png")
    plot_label_breakdown_plotly(results, out_dir / "probe_outcomes")
    plot_label_breakdown_matplotlib(results, out_dir / "probe_outcomes.png")
    plot_recall_by_category_plotly(results, out_dir / "recall_by_category")
    plot_recall_by_category_matplotlib(results, out_dir / "recall_by_category.png")
    plot_latency_bar_plotly(results, out_dir / "latency_bar")
    plot_latency_bar_matplotlib(results, out_dir / "latency_bar.png")
    plot_latency_by_turn_plotly(results, out_dir / "latency_by_turn")
    plot_latency_by_turn_matplotlib(results, out_dir / "latency_by_turn.png")

    cost_table = build_cost_table(results)
    (out_dir / "cost_table.md").write_text(cost_table)

    print("Visualizations written to", out_dir)
