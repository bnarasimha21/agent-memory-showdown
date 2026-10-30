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


def plot_latency_bar_plotly(results: dict, output_path: Path) -> None:
    backends = []
    avg_lats = []
    std_lats = []

    for backend, data in results.items():
        if "error" in data:
            continue
        backends.append(backend)
        avg_lats.append(data["avg_latency_ms"])
        std_lats.append(data["std_latency_ms"])

    colors = [BACKEND_COLORS.get(b, "#888") for b in backends]

    fig = go.Figure(
        go.Bar(
            x=backends,
            y=avg_lats,
            error_y=dict(type="data", array=std_lats, visible=True),
            marker_color=colors,
        )
    )
    fig.update_layout(
        title="Average Retrieval Latency per Backend",
        xaxis_title="Memory Backend",
        yaxis_title="Latency (ms)",
        template="plotly_white",
        width=700,
        height=450,
    )
    fig.write_html(str(output_path.with_suffix(".html")))
    try:
        fig.write_image(str(output_path.with_suffix(".png")))
    except Exception:
        pass


def plot_latency_bar_matplotlib(results: dict, output_path: Path) -> None:
    backends = []
    avg_lats = []
    std_lats = []

    for backend, data in results.items():
        if "error" in data:
            continue
        backends.append(backend)
        avg_lats.append(data["avg_latency_ms"])
        std_lats.append(data["std_latency_ms"])

    colors = [BACKEND_COLORS.get(b, "#888") for b in backends]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(backends, avg_lats, color=colors, yerr=std_lats, capsize=5)
    ax.set_title("Average Retrieval Latency per Backend")
    ax.set_xlabel("Memory Backend")
    ax.set_ylabel("Latency (ms)")
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(str(output_path), dpi=150)
    plt.close()


def build_cost_table(results: dict) -> str:
    """Build a markdown cost comparison table."""
    lines = [
        "| Backend | Avg Tokens/Run | Est. Cost/1K Conversations (USD) |",
        "|---------|---------------|----------------------------------|",
    ]
    for backend, data in results.items():
        if "error" in data:
            lines.append(f"| {backend} | ERROR | ERROR |")
            continue
        avg_tokens = data.get("avg_tokens_per_run", 0)
        cost = data.get("estimated_cost_per_1k_conversations_usd", 0)
        lines.append(f"| {backend} | {avg_tokens:.0f} | ${cost:.4f} |")
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
    plot_latency_bar_plotly(results, out_dir / "latency_bar")
    plot_latency_bar_matplotlib(results, out_dir / "latency_bar.png")

    cost_table = build_cost_table(results)
    (out_dir / "cost_table.md").write_text(cost_table)

    print("Visualizations written to", out_dir)
