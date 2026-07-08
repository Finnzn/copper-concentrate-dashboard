"""Risk summary calculations for simulated price and margin paths."""

from __future__ import annotations

import numpy as np
import pandas as pd

from copper_monte_carlo.config import MonteCarloConfig


def _positive_loss_var(values: np.ndarray, percentile: float = 5.0) -> float:
    threshold = np.percentile(values, percentile)
    return max(0.0, -float(threshold))


def _positive_loss_cvar(values: np.ndarray, percentile: float = 5.0) -> float:
    threshold = np.percentile(values, percentile)
    tail = values[values <= threshold]
    if tail.size == 0:
        return 0.0
    return max(0.0, -float(np.mean(tail)))


def path_percentiles(paths: np.ndarray, confidence_levels: tuple[float, ...]) -> pd.DataFrame:
    """Return percentile bands by month for fan charts."""

    rows = {"month": np.arange(paths.shape[1])}
    for level in confidence_levels:
        rows[f"p{int(level * 100)}"] = np.percentile(paths, level * 100, axis=0)
    return pd.DataFrame(rows)


def maximum_drawdown(paths: np.ndarray) -> float:
    """Average maximum path drawdown, expressed in USD."""

    running_peak = np.maximum.accumulate(paths, axis=1)
    drawdowns = paths - running_peak
    return float(np.mean(np.min(drawdowns, axis=1)))


def risk_summary(
    config: MonteCarloConfig,
    copper_price_paths: np.ndarray,
    margin_paths: np.ndarray,
    unhedged_margin_paths: np.ndarray,
) -> pd.DataFrame:
    """Build a compact risk summary table for the final simulated month."""

    final_price = copper_price_paths[:, -1]
    final_margin = margin_paths[:, -1]
    final_unhedged = unhedged_margin_paths[:, -1]
    var_95 = _positive_loss_var(final_margin)
    cvar_95 = _positive_loss_cvar(final_margin)
    unhedged_var_95 = _positive_loss_var(final_unhedged)
    hedged_variance = float(np.var(final_margin))
    unhedged_variance = float(np.var(final_unhedged))
    hedge_effectiveness = (
        1 - hedged_variance / unhedged_variance if unhedged_variance > 0 else 0.0
    )
    rows = [
        ("Expected final copper price", float(np.mean(final_price))),
        ("Median final copper price", float(np.median(final_price))),
        ("P5 final copper price", float(np.percentile(final_price, 5))),
        ("P95 final copper price", float(np.percentile(final_price, 95))),
        ("Expected margin", float(np.mean(final_margin))),
        ("Median margin", float(np.median(final_margin))),
        ("P5 margin", float(np.percentile(final_margin, 5))),
        ("P95 margin", float(np.percentile(final_margin, 95))),
        ("Probability of loss", float(np.mean(final_margin < config.loss_threshold_usd))),
        ("95% VaR", var_95),
        ("95% CVaR", cvar_95),
        ("Worst 1% average outcome", float(np.mean(final_margin[final_margin <= np.percentile(final_margin, 1)]))),
        ("Worst case margin", float(np.min(final_margin))),
        ("Best case margin", float(np.max(final_margin))),
        ("Average maximum drawdown", maximum_drawdown(margin_paths)),
        ("Probability copper above threshold", float(np.mean(final_price > config.high_copper_threshold_usd_per_tonne))),
        ("Probability copper below threshold", float(np.mean(final_price < config.low_copper_threshold_usd_per_tonne))),
        ("Hedge effectiveness", float(hedge_effectiveness)),
        ("Risk reduction from hedge", float(unhedged_var_95 - var_95)),
    ]
    return pd.DataFrame(rows, columns=["Metric", "Value"])
