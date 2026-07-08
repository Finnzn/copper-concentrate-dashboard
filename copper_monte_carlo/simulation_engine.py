"""Simulation orchestration for copper market and concentrate margin paths."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from copper_monte_carlo.concentrate_valuation import margin_paths
from copper_monte_carlo.config import MonteCarloConfig, config_from_assumptions
from copper_monte_carlo.risk_metrics import path_percentiles, risk_summary
from copper_monte_carlo.stochastic_processes import (
    correlated_standard_normals,
    freight_paths_with_jumps,
    gbm_paths,
    mean_reverting_paths,
)


@dataclass(frozen=True)
class SimulationResult:
    config: MonteCarloConfig
    copper_price_paths: np.ndarray
    tc_paths: np.ndarray
    rc_paths: np.ndarray
    freight_paths: np.ndarray
    fx_paths: np.ndarray
    basis_paths: np.ndarray
    margin_paths: np.ndarray
    unhedged_margin_paths: np.ndarray
    hedge_pnl_paths: np.ndarray
    risk_summary: pd.DataFrame
    price_fan: pd.DataFrame
    margin_fan: pd.DataFrame
    static_values: dict[str, float]


def run_monte_carlo(config: MonteCarloConfig | None = None, **overrides) -> SimulationResult:
    """Run monthly path simulation for copper and physical trade economics."""

    cfg = config or config_from_assumptions(**overrides)
    if config is not None and overrides:
        cfg = MonteCarloConfig(**{**cfg.__dict__, **overrides})

    rng = np.random.default_rng(cfg.random_seed)
    shocks = correlated_standard_normals(
        rng, cfg.n_simulations, cfg.horizon_months, cfg.correlation_matrix
    )
    copper_price_paths = gbm_paths(
        cfg.initial_copper_price_usd_per_tonne,
        cfg.monthly_drift,
        cfg.monthly_volatility,
        shocks[:, :, 0],
        floor=cfg.min_price_floor,
        cap=cfg.max_price_cap,
        jump_probability=cfg.copper_jump_probability,
        jump_mean=cfg.copper_jump_mean,
        jump_volatility=cfg.copper_jump_volatility,
        rng=rng,
    )
    tc_paths = mean_reverting_paths(
        cfg.initial_tc_usd_per_dmt,
        cfg.tc_mean_reversion_level,
        cfg.tc_mean_reversion_speed,
        cfg.tc_volatility,
        shocks[:, :, 1],
        floor=cfg.tc_floor,
        cap=cfg.tc_cap,
    )
    rc_paths = mean_reverting_paths(
        cfg.initial_rc_usd_per_lb,
        cfg.rc_mean_reversion_level,
        cfg.rc_mean_reversion_speed,
        cfg.rc_volatility,
        shocks[:, :, 2],
        floor=cfg.rc_floor,
        cap=cfg.rc_cap,
    )
    freight_paths = freight_paths_with_jumps(
        cfg.initial_freight_usd_per_wmt,
        cfg.freight_mean_reversion_level,
        cfg.freight_mean_reversion_speed,
        cfg.freight_volatility,
        shocks[:, :, 3],
        cfg.freight_jump_probability,
        cfg.freight_jump_size_mean,
        cfg.freight_jump_size_volatility,
        rng,
    )
    fx_paths = gbm_paths(
        cfg.initial_fx_rate,
        (1 + cfg.fx_drift) ** (1 / 12) - 1,
        cfg.fx_volatility / np.sqrt(12),
        shocks[:, :, 4],
        floor=0.0001,
        rng=rng,
    )
    basis_paths = mean_reverting_paths(
        cfg.initial_basis_usd_per_tonne,
        cfg.basis_mean_reversion_level,
        cfg.basis_mean_reversion_speed,
        cfg.basis_volatility,
        shocks[:, :, 5],
    )
    valuation = margin_paths(
        cfg, copper_price_paths, tc_paths, rc_paths, freight_paths, basis_paths
    )
    simulated_margin_paths = valuation["simulated_margin_paths"]
    unhedged_margin_paths = valuation["unhedged_margin"]
    return SimulationResult(
        config=cfg,
        copper_price_paths=copper_price_paths,
        tc_paths=tc_paths,
        rc_paths=rc_paths,
        freight_paths=freight_paths,
        fx_paths=fx_paths,
        basis_paths=basis_paths,
        margin_paths=simulated_margin_paths,
        unhedged_margin_paths=unhedged_margin_paths,
        hedge_pnl_paths=valuation["hedge_pnl"],
        risk_summary=risk_summary(
            cfg, copper_price_paths, simulated_margin_paths, unhedged_margin_paths
        ),
        price_fan=path_percentiles(copper_price_paths, cfg.confidence_levels),
        margin_fan=path_percentiles(simulated_margin_paths, cfg.confidence_levels),
        static_values={
            "dry_metric_tonnes": float(valuation["dry_metric_tonnes"]),
            "contained_copper_tonnes": float(valuation["contained_copper_tonnes"]),
            "payable_copper_tonnes": float(valuation["payable_copper_tonnes"]),
            "byproduct_credit_usd": float(valuation["byproduct_credit_usd"]),
        },
    )


def paths_to_frame(paths: np.ndarray, value_name: str, max_paths: int | None = None) -> pd.DataFrame:
    """Convert path arrays to long-form data for export or plotting."""

    selected = paths if max_paths is None else paths[:max_paths]
    frame = pd.DataFrame(selected).reset_index(names="simulation")
    return frame.melt(id_vars="simulation", var_name="month", value_name=value_name)
