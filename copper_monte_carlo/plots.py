"""Plotly charts for Monte Carlo price and margin results."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from copper_monte_carlo.simulation_engine import SimulationResult


CHART_LAYOUT = {
    "template": "plotly_white",
    "plot_bgcolor": "#FFFFFF",
    "paper_bgcolor": "#FFFFFF",
    "font": {"color": "#18212B"},
    "xaxis": {"gridcolor": "rgba(24, 33, 43, 0.12)", "zerolinecolor": "#5B6775"},
    "yaxis": {"gridcolor": "rgba(24, 33, 43, 0.12)", "zerolinecolor": "#5B6775"},
    "legend": {"font": {"color": "#18212B"}, "orientation": "h"},
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
                fillcolor="rgba(168, 67, 62, 0.18)",
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
                fillcolor="rgba(40, 120, 95, 0.20)",
            )
        )
    median_col = "p50" if "p50" in fan.columns else fan.columns[len(fan.columns) // 2]
    fig.add_trace(
        go.Scatter(
            x=x,
            y=fan[median_col],
            mode="lines",
            name="Median",
            line=dict(color="#9F5B35", width=3),
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title="Month",
        yaxis_title=yaxis_title,
        height=520,
        **CHART_LAYOUT,
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
        "rgba(66, 110, 134, 0.34)",
        "rgba(40, 120, 95, 0.30)",
        "rgba(159, 91, 53, 0.28)",
        "rgba(91, 103, 117, 0.26)",
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
    for percentile, color in [(5, "#A8433E"), (95, "#A8433E")]:
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
            line=dict(color="#9F5B35", width=3),
        )
    )
    fig.update_layout(
        title="Sampled Copper Price Paths",
        xaxis_title="Month",
        yaxis_title="Copper price (USD/t)",
        height=540,
        **CHART_LAYOUT,
    )
    return fig


def copper_fan_chart(result: SimulationResult) -> go.Figure:
    return _fan_chart(result.price_fan, "Copper Price Percentile Fan", "Copper price (USD/t)")


def margin_fan_chart(result: SimulationResult) -> go.Figure:
    return _fan_chart(result.margin_fan, "Trade Margin Percentile Fan", "Margin (USD)")


def final_distribution(values, title: str, xaxis_title: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=values,
            nbinsx=60,
            marker_color="#28785F",
            name="Distribution",
        )
    )
    markers = {
        "Mean": np.mean(values),
        "Median": np.median(values),
        "P5": np.percentile(values, 5),
        "P95": np.percentile(values, 95),
    }
    colors = {"Mean": "#9F5B35", "Median": "#28785F", "P5": "#A8433E", "P95": "#A8433E"}
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
        **CHART_LAYOUT,
    )
    return fig
