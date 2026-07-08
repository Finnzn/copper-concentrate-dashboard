import numpy as np

from copper_monte_carlo.config import (
    config_from_assumptions,
    load_default_assumptions,
    validate_assumptions,
)
from copper_monte_carlo.concentrate_valuation import static_concentrate_values
from copper_monte_carlo.risk_metrics import risk_summary
from copper_monte_carlo.simulation_engine import run_monte_carlo


def small_config(**overrides):
    values = {
        "n_simulations": 500,
        "horizon_months": 12,
        "random_seed": 7,
    }
    values.update(overrides)
    return config_from_assumptions(load_default_assumptions(), **values)


def test_default_assumptions_load_with_fallback_metadata():
    assumptions = load_default_assumptions()

    assert assumptions["copper_price"]["initial_copper_price_usd_per_tonne"] == 12000
    assert (
        assumptions["metadata"]["input_sources"]["Copper price"]["source"]
        == "fallback_assumption"
    )


def test_no_negative_copper_prices_and_quality_relationships():
    config = small_config()
    result = run_monte_carlo(config)
    static = static_concentrate_values(config)

    assert np.all(result.copper_price_paths >= config.min_price_floor)
    assert static.dry_metric_tonnes < config.wet_metric_tonnes
    assert static.payable_copper_tonnes <= static.contained_copper_tonnes


def test_probability_values_are_between_zero_and_one():
    result = run_monte_carlo(small_config())
    summary = result.risk_summary.set_index("Metric")["Value"]

    for metric in [
        "Probability of loss",
        "Probability copper above threshold",
        "Probability copper below threshold",
    ]:
        assert 0 <= summary[metric] <= 1


def test_var_and_cvar_are_consistent_loss_style_metrics():
    result = run_monte_carlo(small_config())
    summary = result.risk_summary.set_index("Metric")["Value"]

    assert summary["95% VaR"] >= 0
    assert summary["95% CVaR"] >= summary["95% VaR"]


def test_zero_volatility_creates_deterministic_copper_path_without_jumps():
    config = small_config(
        annual_volatility=0.0,
        annual_drift=0.0,
        copper_jump_probability=0.0,
        initial_copper_price_usd_per_tonne=12000.0,
    )
    result = run_monte_carlo(config)

    assert np.allclose(result.copper_price_paths, 12000.0)


def test_full_hedge_reduces_price_exposure_variance():
    unhedged = run_monte_carlo(small_config(hedge_enabled=False, hedge_ratio=0.0))
    hedged = run_monte_carlo(small_config(hedge_enabled=True, hedge_ratio=1.0))

    assert np.var(hedged.margin_paths[:, -1]) < np.var(unhedged.margin_paths[:, -1])


def test_validation_warns_for_small_simulation_and_fallbacks():
    warnings = validate_assumptions(small_config(n_simulations=100))

    assert any("very small" in warning for warning in warnings)
    assert any("Fallback assumptions" in warning for warning in warnings)


def test_risk_summary_shape_for_manual_arrays():
    config = small_config(n_simulations=10, horizon_months=2)
    copper = np.full((10, 3), 12000.0)
    margin = np.linspace(-100, 100, 30).reshape(10, 3)
    summary = risk_summary(config, copper, margin, margin)

    assert list(summary.columns) == ["Metric", "Value"]
    assert "95% VaR" in summary["Metric"].tolist()


def test_all_trade_modes_run_without_shape_changes():
    modes = [
        "concentrate_merchant",
        "smelter_conversion",
        "refined_copper_trade",
        "integrated_conversion",
    ]

    for mode in modes:
        result = run_monte_carlo(small_config(trade_mode=mode, horizon_months=3))
        assert result.margin_paths.shape == (500, 4)
        assert np.isfinite(result.margin_paths).all()
