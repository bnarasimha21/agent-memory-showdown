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
    with open(results_path) as f:
        return json.load(f)


def _get_recall_curve_data(results: dict) -> dict:
    """Extract recall accuracy at each probe turn for each backend.

    The new results format uses 'recall_accuracy_by_probe_turn' keyed by the
    turn where probes were asked (15, 25, 35, 50).
    """
    curves = {}
    for backend, data in results.items():
        if "error" in data:
            continue

        by_probe = data.get("recall_accuracy_by_probe_turn", {})
        if not by_probe:
            by_seed = data.get("recall_accuracy_by_seed_turn", {})
            if by_seed:
                sorted_turns = sorted(by_seed.keys(), key=int)
                curves[backend] = {
                    "turns": [int(t) for t in sorted_turns],
                    "correct_rates": [by_seed[t]["correct_rate"] for t in sorted_turns],
                }
            continue

        sorted_probe_turns = sorted(by_probe.keys(), key=int)
        curves[backend] = {
            "turns": [int(t) for t in sorted_probe_turns],
            "correct_rates": [
                by_probe[t]["correct_rate"] for t in sorted_probe_turns
            ],
        }
    return curves


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
                line=dict(color=color, width=2),
                marker=dict(size=8),
            )
        )

    fig.update_layout(
        title="Memory Decay Curve: Recall Accuracy by Probe Turn",
        xaxis_title="Conversation Turn (Probe Point)",
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
        ax.plot(
            data["turns"],
            [r * 100 for r in data["correct_rates"]],
            marker="o",
            color=color,
            linewidth=2,
            label=backend,
        )

    ax.set_title("Memory Decay Curve: Recall Accuracy by Probe Turn")
    ax.set_xlabel("Conversation Turn (Probe Point)")
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
    plot_latency_bar_plotly(results, out_dir / "latency_bar")
    plot_latency_bar_matplotlib(results, out_dir / "latency_bar.png")

    cost_table = build_cost_table(results)
    (out_dir / "cost_table.md").write_text(cost_table)

    print("Visualizations written to", out_dir)
