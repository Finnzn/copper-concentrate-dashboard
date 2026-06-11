import pytest

from src.risk import (
    sensitivity_heatmap,
    sensitivity_variable_names,
    tornado_impacts,
    two_way_sensitivity_heatmap,
)
from src.scenarios import build_scenarios
from src.valuation import LB_PER_METRIC_TONNE, ConcentrateAssumptions, calculate_valuation


def base_assumptions(**overrides) -> ConcentrateAssumptions:
    values = {
        "wet_metric_tonnes": 10_000.0,
        "moisture_percentage": 8.0,
        "copper_grade_percentage": 26.0,
        "payable_copper_percentage": 96.5,
        "lme_copper_price_usd_per_tonne": 9_500.0,
        "tc_usd_per_dmt": 80.0,
        "rc_cents_per_lb": 8.0,
        "freight_usd_per_dmt": 55.0,
        "impurity_penalty_usd_per_dmt": 12.0,
    }
    values.update(overrides)
    return ConcentrateAssumptions(**values)


def test_base_valuation_uses_dmt_and_lower_payable_copper_rule():
    result = calculate_valuation(base_assumptions())

    assert result.dry_metric_tonnes == pytest.approx(9_200.0)
    assert result.contained_copper_tonnes == pytest.approx(2_392.0)
    assert result.payable_copper_by_percentage_tonnes == pytest.approx(2_308.28)
    assert result.payable_copper_by_deduction_tonnes == pytest.approx(2_300.0)
    assert result.payable_copper_tonnes == pytest.approx(2_300.0)
    assert result.payable_copper_lb == pytest.approx(2_300.0 * LB_PER_METRIC_TONNE)


def test_rc_tc_precious_metal_and_financing_components_are_calculated():
    result = calculate_valuation(base_assumptions())

    assert result.treatment_charge_usd == pytest.approx(736_000.0)
    assert result.refining_charge_usd == pytest.approx(
        2_300.0 * LB_PER_METRIC_TONNE * 0.08
    )
    assert result.gold_credit_usd > 700_000
    assert result.silver_credit_usd > 250_000
    assert result.financing_cost_usd > 0
    assert result.net_value_usd == pytest.approx(20_922_713.51, abs=0.01)


def test_impurity_threshold_penalties_apply_only_above_thresholds():
    result = calculate_valuation(
        base_assumptions(arsenic_ppm=3_000.0, bismuth_ppm=1_500.0, fluorine_ppm=500.0)
    )

    assert result.arsenic_penalty_usd == pytest.approx(9_200.0 * 3.0)
    assert result.bismuth_penalty_usd == pytest.approx(9_200.0 * 8.0)
    assert result.fluorine_penalty_usd == pytest.approx(0.0)
    assert result.total_impurity_penalty_usd == pytest.approx(
        result.flat_impurity_penalty_usd
        + result.arsenic_penalty_usd
        + result.bismuth_penalty_usd
        + result.fluorine_penalty_usd
    )


def test_zero_wet_tonnes_does_not_divide_by_zero():
    result = calculate_valuation(base_assumptions(wet_metric_tonnes=0.0))

    assert result.dry_metric_tonnes == 0.0
    assert result.value_per_dmt_usd == 0.0
    assert result.net_value_usd == 0.0


def test_risk_and_scenario_outputs_have_expected_shapes():
    assumptions = base_assumptions()

    assert sensitivity_heatmap(assumptions).shape == (81, 3)
    assert build_scenarios(assumptions).shape == (6, 8)
    tornado = tornado_impacts(assumptions)
    assert list(tornado.columns) == [
        "Driver",
        "Low impact USD",
        "High impact USD",
        "Absolute max impact USD",
    ]
    assert tornado["Absolute max impact USD"].is_monotonic_increasing


def test_two_way_sensitivity_supports_configured_driver_pairs():
    assumptions = base_assumptions()

    heatmap = two_way_sensitivity_heatmap(
        assumptions,
        x_variable="Copper price",
        y_variable="Freight",
        steps=5,
    )

    assert heatmap.shape == (25, 3)
    assert list(heatmap.columns) == [
        "Copper price USD/t",
        "Freight USD/dmt",
        "Net value USD",
    ]
    assert "Arsenic" in sensitivity_variable_names()


def test_two_way_sensitivity_rejects_same_driver_pair():
    with pytest.raises(ValueError, match="two different"):
        two_way_sensitivity_heatmap(
            base_assumptions(),
            x_variable="TC",
            y_variable="TC",
        )
