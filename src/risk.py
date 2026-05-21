"""Sensitivity and risk calculations for the dashboard."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from src.valuation import ConcentrateAssumptions, calculate_valuation


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
        ("TC decrease", replace(assumptions, tc_usd_per_dmt=max(0.0, assumptions.tc_usd_per_dmt - tc_move_usd_per_dmt))),
        ("TC increase", replace(assumptions, tc_usd_per_dmt=assumptions.tc_usd_per_dmt + tc_move_usd_per_dmt)),
        ("RC decrease", replace(assumptions, rc_cents_per_lb=max(0.0, assumptions.rc_cents_per_lb - rc_move_cents_per_lb))),
        ("RC increase", replace(assumptions, rc_cents_per_lb=assumptions.rc_cents_per_lb + rc_move_cents_per_lb)),
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
