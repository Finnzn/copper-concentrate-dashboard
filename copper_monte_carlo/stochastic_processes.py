"""Vectorized stochastic process helpers for monthly copper simulations."""

from __future__ import annotations

import numpy as np


def correlated_standard_normals(
    rng: np.random.Generator,
    n_simulations: int,
    n_steps: int,
    correlation_matrix: np.ndarray,
) -> np.ndarray:
    """Generate correlated shocks with shape steps x simulations x variables."""

    matrix = np.array(correlation_matrix, dtype=float)
    jitter = np.eye(matrix.shape[0]) * 1e-10
    cholesky = np.linalg.cholesky(matrix + jitter)
    independent = rng.standard_normal((n_steps, n_simulations, matrix.shape[0]))
    return independent @ cholesky.T


def gbm_paths(
    initial_value: float,
    monthly_drift: float,
    monthly_volatility: float,
    shocks: np.ndarray,
    floor: float = 0.0,
    cap: float | None = None,
    jump_probability: float = 0.0,
    jump_mean: float = 0.0,
    jump_volatility: float = 0.0,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Simulate positive GBM-style paths using monthly log returns."""

    n_steps, n_simulations = shocks.shape
    paths = np.empty((n_simulations, n_steps + 1))
    paths[:, 0] = initial_value
    jump_rng = rng or np.random.default_rng()
    jump_mask = jump_rng.random((n_steps, n_simulations)) < jump_probability
    jumps = jump_rng.normal(jump_mean, jump_volatility, (n_steps, n_simulations))
    log_returns = (
        monthly_drift
        - 0.5 * monthly_volatility**2
        + monthly_volatility * shocks
        + jump_mask * jumps
    )
    for step in range(n_steps):
        paths[:, step + 1] = paths[:, step] * np.exp(log_returns[step])
        paths[:, step + 1] = np.maximum(paths[:, step + 1], floor)
        if cap is not None:
            paths[:, step + 1] = np.minimum(paths[:, step + 1], cap)
    return paths


def mean_reverting_paths(
    initial_value: float,
    long_term_mean: float,
    speed: float,
    volatility: float,
    shocks: np.ndarray,
    floor: float | None = None,
    cap: float | None = None,
) -> np.ndarray:
    """Simulate an Ornstein-Uhlenbeck-style arithmetic process."""

    n_steps, n_simulations = shocks.shape
    paths = np.empty((n_simulations, n_steps + 1))
    paths[:, 0] = initial_value
    for step in range(n_steps):
        paths[:, step + 1] = (
            paths[:, step]
            + speed * (long_term_mean - paths[:, step])
            + volatility * shocks[step]
        )
        if floor is not None:
            paths[:, step + 1] = np.maximum(paths[:, step + 1], floor)
        if cap is not None:
            paths[:, step + 1] = np.minimum(paths[:, step + 1], cap)
    return paths


def freight_paths_with_jumps(
    initial_value: float,
    long_term_mean: float,
    speed: float,
    volatility: float,
    shocks: np.ndarray,
    jump_probability: float,
    jump_size_mean: float,
    jump_size_volatility: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """Simulate mean-reverting freight with disruption jumps."""

    n_steps, n_simulations = shocks.shape
    paths = np.empty((n_simulations, n_steps + 1))
    paths[:, 0] = initial_value
    jump_mask = rng.random((n_steps, n_simulations)) < jump_probability
    jump_sizes = rng.normal(jump_size_mean, jump_size_volatility, (n_steps, n_simulations))
    for step in range(n_steps):
        paths[:, step + 1] = (
            paths[:, step]
            + speed * (long_term_mean - paths[:, step])
            + volatility * shocks[step]
            + jump_mask[step] * np.maximum(0.0, jump_sizes[step])
        )
        paths[:, step + 1] = np.maximum(paths[:, step + 1], 0.0)
    return paths
