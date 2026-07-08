"""Plotly charts for Monte Carlo price and margin results."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from copper_monte_carlo.simulation_engine import SimulationResult


DARK_LAYOUT = {
    "template": "plotly_dark",
    "plot_bgcolor": "#111827",
    "paper_bgcolor": "#111827",
    "font": {"color": "#F3F4F6"},
    "xaxis": {"gridcolor": "rgba(243, 244, 246, 0.16)", "zerolinecolor": "#9CA3AF"},
    "yaxis": {"gridcolor": "rgba(243, 244, 246, 0.16)", "zerolinecolor": "#9CA3AF"},
    "legend": {"font": {"color": "#F3F4F6"}},
}


def _fan_chart(fan, title: str, yaxis_title: str) -> go.Figure:
    fig = go.Figure()
    x = fan["month"]
    if {"p5", "p95"}.issubset(fan.columns):
        fig.add_trace(go.Scatter(x=x, y=fan["p95"], line=dict(width=0), showlegend=False))
        fig.add_trace(
            go.Scatter(
                x=x,
                y=fan["p5"],
                fill="tonexty",
                name="P5-P95",
                line=dict(width=0),
                fillcolor="rgba(248, 113, 113, 0.24)",
            )
        )
    if {"p10", "p90"}.issubset(fan.columns):
        fig.add_trace(go.Scatter(x=x, y=fan["p90"], line=dict(width=0), showlegend=False))
        fig.add_trace(
            go.Scatter(
                x=x,
                y=fan["p10"],
                fill="tonexty",
                name="P10-P90",
                line=dict(width=0),
                fillcolor="rgba(45, 212, 191, 0.26)",
            )
        )
    median_col = "p50" if "p50" in fan.columns else fan.columns[len(fan.columns) // 2]
    fig.add_trace(
        go.Scatter(
            x=x,
            y=fan[median_col],
            mode="lines",
            name="Median",
            line=dict(color="#FACC15", width=3),
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="Month",
        yaxis_title=yaxis_title,
        height=520,
        **DARK_LAYOUT,
    )
    return fig


def copper_spider_plot(result: SimulationResult, sample_size: int = 90) -> go.Figure:
    """Show a sampled spaghetti plot with median path overlay."""

    paths = result.copper_price_paths
    sample_size = min(sample_size, paths.shape[0])
    rng = np.random.default_rng(result.config.random_seed)
    sample = rng.choice(paths.shape[0], size=sample_size, replace=False)
    months = np.arange(paths.shape[1])
    fig = go.Figure()
    path_colors = [
        "rgba(96, 165, 250, 0.42)",
        "rgba(45, 212, 191, 0.36)",
        "rgba(251, 146, 60, 0.34)",
        "rgba(209, 213, 219, 0.28)",
    ]
    for idx in sample:
        color = path_colors[int(idx) % len(path_colors)]
        fig.add_trace(
            go.Scatter(
                x=months,
                y=paths[idx],
                mode="lines",
                line=dict(color=color, width=1.15),
                showlegend=False,
                hoverinfo="skip",
            )
        )
    for percentile, color in [(5, "#F87171"), (95, "#F87171")]:
        fig.add_trace(
            go.Scatter(
                x=months,
                y=np.percentile(paths, percentile, axis=0),
                mode="lines",
                name=f"P{percentile}",
                line=dict(color=color, width=1.8, dash="dot"),
            )
        )
    fig.add_trace(
        go.Scatter(
            x=months,
            y=np.median(paths, axis=0),
            mode="lines",
            name="Median",
            line=dict(color="#FACC15", width=3),
        )
    )
    fig.update_layout(
        title="Copper Price Spider Plot",
        xaxis_title="Month",
        yaxis_title="Copper price USD/t",
        height=540,
        **DARK_LAYOUT,
    )
    return fig


def copper_fan_chart(result: SimulationResult) -> go.Figure:
    return _fan_chart(result.price_fan, "Copper Price Fan Chart", "Copper price USD/t")


def margin_fan_chart(result: SimulationResult) -> go.Figure:
    return _fan_chart(result.margin_fan, "Physical Trade Margin Fan Chart", "Margin USD")


def final_distribution(values, title: str, xaxis_title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=values,
            nbinsx=60,
            marker_color="#2DD4BF",
            name="Distribution",
        )
    )
    markers = {
        "Mean": np.mean(values),
        "Median": np.median(values),
        "P5": np.percentile(values, 5),
        "P95": np.percentile(values, 95),
    }
    colors = {"Mean": "#FACC15", "Median": "#2DD4BF", "P5": "#F87171", "P95": "#F87171"}
    for label, value in markers.items():
        fig.add_vline(
            x=float(value),
            line_width=2,
            line_dash="dash",
            line_color=colors[label],
            annotation_text=label,
        )
    fig.update_layout(
        title=title,
        xaxis_title=xaxis_title,
        yaxis_title="Count",
        height=500,
        **DARK_LAYOUT,
    )
    return fig
