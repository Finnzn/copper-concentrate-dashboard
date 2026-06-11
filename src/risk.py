"""Sensitivity and risk calculations for the dashboard."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from src.valuation import ConcentrateAssumptions, calculate_valuation


SENSITIVITY_VARIABLES = {
    "Copper price": {
        "field": "lme_copper_price_usd_per_tonne",
        "label": "Copper price USD/t",
        "mode": "percentage",
        "range": 10.0,
    },
    "TC": {
        "field": "tc_usd_per_dmt",
        "label": "TC USD/dmt",
        "mode": "absolute",
        "range": 40.0,
    },
    "RC": {
        "field": "rc_cents_per_lb",
        "label": "RC US cents/lb",
        "mode": "absolute",
        "range": 3.0,
    },
    "Freight": {
        "field": "freight_usd_per_dmt",
        "label": "Freight USD/dmt",
        "mode": "absolute",
        "range": 25.0,
    },
    "Copper grade": {
        "field": "copper_grade_percentage",
        "label": "Copper grade %",
        "mode": "absolute",
        "range": 3.0,
    },
    "Moisture": {
        "field": "moisture_percentage",
        "label": "Moisture %",
        "mode": "absolute",
        "range": 2.0,
    },
    "Arsenic": {
        "field": "arsenic_ppm",
        "label": "Arsenic ppm",
        "mode": "absolute",
        "range": 1500.0,
    },
    "Gold price": {
        "field": "gold_price_usd_per_oz",
        "label": "Gold price USD/oz",
        "mode": "percentage",
        "range": 10.0,
    },
    "Financing rate": {
        "field": "annual_financing_rate_percentage",
        "label": "Financing rate %",
        "mode": "absolute",
        "range": 2.0,
    },
}


def sensitivity_variable_names() -> list[str]:
    """Return display names available for two-way sensitivity analysis."""

    return list(SENSITIVITY_VARIABLES.keys())


def sensitivity_axis_values(
    assumptions: ConcentrateAssumptions, variable_name: str, steps: int = 9
) -> tuple[str, np.ndarray]:
    """Build axis values for one configured sensitivity variable."""

    variable = SENSITIVITY_VARIABLES[variable_name]
    base_value = float(getattr(assumptions, variable["field"]))
    range_value = float(variable["range"])

    if variable["mode"] == "percentage":
        low = base_value * (1 - range_value / 100)
        high = base_value * (1 + range_value / 100)
    else:
        low = base_value - range_value
        high = base_value + range_value

    low = max(0.0, low)
    return variable["label"], np.linspace(low, high, steps)


def copper_price_move_impact(
    assumptions: ConcentrateAssumptions, move_percentage: float = 5.0
) -> pd.DataFrame:
    """Show the effect of an up/down copper price move on gross and net value."""

    rows = []
    for label, multiplier in [
        (f"-{move_percentage:.0f}% copper price", 1 - move_percentage / 100),
        ("Base case", 1.0),
        (f"+{move_percentage:.0f}% copper price", 1 + move_percentage / 100),
    ]:
        scenario = replace(
            assumptions,
            lme_copper_price_usd_per_tonne=(
                assumptions.lme_copper_price_usd_per_tonne * multiplier
            ),
        )
        result = calculate_valuation(scenario)
        rows.append(
            {
                "Case": label,
                "LME copper price USD/t": scenario.lme_copper_price_usd_per_tonne,
                "Gross copper value USD": result.gross_copper_value_usd,
                "Net shipment value USD": result.net_value_usd,
            }
        )
    return pd.DataFrame(rows)


def charge_move_impact(
    assumptions: ConcentrateAssumptions,
    tc_move_usd_per_dmt: float = 10.0,
    rc_move_cents_per_lb: float = 2.0,
) -> pd.DataFrame:
    """Calculate the value impact of TC and RC increases/decreases."""

    base_value = calculate_valuation(assumptions).net_value_usd
    cases = [
        (
            "TC decrease",
            replace(
                assumptions,
                tc_usd_per_dmt=max(
                    0.0, assumptions.tc_usd_per_dmt - tc_move_usd_per_dmt
                ),
            ),
        ),
        (
            "TC increase",
            replace(
                assumptions,
                tc_usd_per_dmt=assumptions.tc_usd_per_dmt + tc_move_usd_per_dmt,
            ),
        ),
        (
            "RC decrease",
            replace(
                assumptions,
                rc_cents_per_lb=max(
                    0.0, assumptions.rc_cents_per_lb - rc_move_cents_per_lb
                ),
            ),
        ),
        (
            "RC increase",
            replace(
                assumptions,
                rc_cents_per_lb=assumptions.rc_cents_per_lb + rc_move_cents_per_lb,
            ),
        ),
    ]

    rows = []
    for case, scenario in cases:
        value = calculate_valuation(scenario).net_value_usd
        rows.append(
            {
                "Risk factor": case,
                "Net shipment value USD": value,
                "Impact vs base USD": value - base_value,
            }
        )
    return pd.DataFrame(rows)


def sensitivity_heatmap(
    assumptions: ConcentrateAssumptions,
    price_steps: int = 9,
    tc_steps: int = 9,
    price_range_percentage: float = 10.0,
    tc_range_usd_per_dmt: float = 40.0,
) -> pd.DataFrame:
    """Create a grid of net values across copper price and TC assumptions."""

    price_low = assumptions.lme_copper_price_usd_per_tonne * (
        1 - price_range_percentage / 100
    )
    price_high = assumptions.lme_copper_price_usd_per_tonne * (
        1 + price_range_percentage / 100
    )
    tc_low = max(0.0, assumptions.tc_usd_per_dmt - tc_range_usd_per_dmt)
    tc_high = assumptions.tc_usd_per_dmt + tc_range_usd_per_dmt

    prices = np.linspace(price_low, price_high, price_steps)
    tcs = np.linspace(tc_low, tc_high, tc_steps)

    rows = []
    for tc in tcs:
        for price in prices:
            scenario = replace(
                assumptions,
                lme_copper_price_usd_per_tonne=float(price),
                tc_usd_per_dmt=float(tc),
            )
            rows.append(
                {
                    "TC USD/dmt": round(tc, 2),
                    "Copper price USD/t": round(price, 2),
                    "Net value USD": calculate_valuation(scenario).net_value_usd,
                }
            )
    return pd.DataFrame(rows)


def two_way_sensitivity_heatmap(
    assumptions: ConcentrateAssumptions,
    x_variable: str,
    y_variable: str,
    steps: int = 9,
) -> pd.DataFrame:
    """Create a grid of net values across any two configured variables."""

    if x_variable == y_variable:
        raise ValueError("Choose two different sensitivity variables.")
    if x_variable not in SENSITIVITY_VARIABLES:
        raise ValueError(f"Unknown x sensitivity variable: {x_variable}")
    if y_variable not in SENSITIVITY_VARIABLES:
        raise ValueError(f"Unknown y sensitivity variable: {y_variable}")

    x_label, x_values = sensitivity_axis_values(assumptions, x_variable, steps)
    y_label, y_values = sensitivity_axis_values(assumptions, y_variable, steps)
    x_field = SENSITIVITY_VARIABLES[x_variable]["field"]
    y_field = SENSITIVITY_VARIABLES[y_variable]["field"]

    rows = []
    for y_value in y_values:
        for x_value in x_values:
            scenario = replace(
                assumptions,
                **{
                    x_field: float(x_value),
                    y_field: float(y_value),
                },
            )
            rows.append(
                {
                    x_label: round(float(x_value), 2),
                    y_label: round(float(y_value), 2),
                    "Net value USD": calculate_valuation(scenario).net_value_usd,
                }
            )
    return pd.DataFrame(rows)


def largest_selected_risk_driver(
    assumptions: ConcentrateAssumptions,
    copper_move_percentage: float = 5.0,
    tc_move_usd_per_dmt: float = 10.0,
    rc_move_cents_per_lb: float = 2.0,
) -> tuple[str, float]:
    """Identify the selected variable with the largest absolute impact."""

    base_value = calculate_valuation(assumptions).net_value_usd
    scenarios = {
        "Copper price +5%": replace(
            assumptions,
            lme_copper_price_usd_per_tonne=assumptions.lme_copper_price_usd_per_tonne
            * (1 + copper_move_percentage / 100),
        ),
        "TC +10 USD/dmt": replace(
            assumptions,
            tc_usd_per_dmt=assumptions.tc_usd_per_dmt + tc_move_usd_per_dmt,
        ),
        "RC +2 US¢/lb": replace(
            assumptions,
            rc_cents_per_lb=assumptions.rc_cents_per_lb + rc_move_cents_per_lb,
        ),
    }
    impacts = {
        name: calculate_valuation(scenario).net_value_usd - base_value
        for name, scenario in scenarios.items()
    }
    driver = max(impacts, key=lambda key: abs(impacts[key]))
    return driver, impacts[driver]


def tornado_impacts(assumptions: ConcentrateAssumptions) -> pd.DataFrame:
    """Rank selected valuation drivers by low/high impact versus base value."""

    base_value = calculate_valuation(assumptions).net_value_usd
    shock_definitions = [
        (
            "Copper price +/-5%",
            replace(
                assumptions,
                lme_copper_price_usd_per_tonne=assumptions.lme_copper_price_usd_per_tonne
                * 0.95,
            ),
            replace(
                assumptions,
                lme_copper_price_usd_per_tonne=assumptions.lme_copper_price_usd_per_tonne
                * 1.05,
            ),
        ),
        (
            "TC +/-10 USD/dmt",
            replace(
                assumptions,
                tc_usd_per_dmt=max(0.0, assumptions.tc_usd_per_dmt - 10.0),
            ),
            replace(assumptions, tc_usd_per_dmt=assumptions.tc_usd_per_dmt + 10.0),
        ),
        (
            "RC +/-2 USc/lb",
            replace(
                assumptions,
                rc_cents_per_lb=max(0.0, assumptions.rc_cents_per_lb - 2.0),
            ),
            replace(assumptions, rc_cents_per_lb=assumptions.rc_cents_per_lb + 2.0),
        ),
        (
            "Freight +/-15 USD/dmt",
            replace(
                assumptions,
                freight_usd_per_dmt=max(0.0, assumptions.freight_usd_per_dmt - 15.0),
            ),
            replace(
                assumptions,
                freight_usd_per_dmt=assumptions.freight_usd_per_dmt + 15.0,
            ),
        ),
        (
            "Moisture +/-1 pct point",
            replace(
                assumptions,
                moisture_percentage=max(0.0, assumptions.moisture_percentage - 1.0),
            ),
            replace(
                assumptions,
                moisture_percentage=min(100.0, assumptions.moisture_percentage + 1.0),
            ),
        ),
        (
            "Copper grade +/-1 pct point",
            replace(
                assumptions,
                copper_grade_percentage=max(
                    0.0, assumptions.copper_grade_percentage - 1.0
                ),
            ),
            replace(
                assumptions,
                copper_grade_percentage=min(
                    100.0, assumptions.copper_grade_percentage + 1.0
                ),
            ),
        ),
        (
            "Gold price +/-10%",
            replace(
                assumptions,
                gold_price_usd_per_oz=assumptions.gold_price_usd_per_oz * 0.90,
            ),
            replace(
                assumptions,
                gold_price_usd_per_oz=assumptions.gold_price_usd_per_oz * 1.10,
            ),
        ),
        (
            "Financing rate +/-2 pct points",
            replace(
                assumptions,
                annual_financing_rate_percentage=max(
                    0.0, assumptions.annual_financing_rate_percentage - 2.0
                ),
            ),
            replace(
                assumptions,
                annual_financing_rate_percentage=assumptions.annual_financing_rate_percentage
                + 2.0,
            ),
        ),
    ]

    rows = []
    for driver, low_case, high_case in shock_definitions:
        low_impact = calculate_valuation(low_case).net_value_usd - base_value
        high_impact = calculate_valuation(high_case).net_value_usd - base_value
        rows.append(
            {
                "Driver": driver,
                "Low impact USD": low_impact,
                "High impact USD": high_impact,
                "Absolute max impact USD": max(abs(low_impact), abs(high_impact)),
            }
        )

    return (
        pd.DataFrame(rows)
        .sort_values("Absolute max impact USD", ascending=True)
        .reset_index(drop=True)
    )
