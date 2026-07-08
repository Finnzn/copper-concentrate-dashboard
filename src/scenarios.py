"""Scenario definitions for concentrate trade economics."""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from src.valuation import ConcentrateAssumptions, calculate_valuation


def build_scenarios(assumptions: ConcentrateAssumptions) -> pd.DataFrame:
    """Return standard commercial scenarios used in the dashboard."""

    scenario_inputs = {
        "Base case": assumptions,
        "Lower copper price": replace(
            assumptions,
            lme_copper_price_usd_per_tonne=assumptions.lme_copper_price_usd_per_tonne
            * 0.95,
        ),
        "Higher copper price": replace(
            assumptions,
            lme_copper_price_usd_per_tonne=assumptions.lme_copper_price_usd_per_tonne
            * 1.05,
        ),
        "Lower TC/RC market": replace(
            assumptions,
            tc_usd_per_dmt=assumptions.tc_usd_per_dmt - 15,
            rc_cents_per_lb=assumptions.rc_cents_per_lb - 3,
        ),
        "Higher freight/logistics cost": replace(
            assumptions,
            freight_usd_per_dmt=assumptions.freight_usd_per_dmt + 20,
        ),
        "High impurity penalty case": replace(
            assumptions,
            impurity_penalty_usd_per_dmt=assumptions.impurity_penalty_usd_per_dmt
            + 25,
        ),
    }

    rows = []
    for name, scenario in scenario_inputs.items():
        result = calculate_valuation(scenario)
        rows.append(
            {
                "Scenario": name,
                "Copper price USD/t": scenario.lme_copper_price_usd_per_tonne,
                "TC USD/dmt": scenario.tc_usd_per_dmt,
                "RC US¢/lb": scenario.rc_cents_per_lb,
                "Freight USD/dmt": scenario.freight_usd_per_dmt,
                "Impurity penalty USD/dmt": scenario.impurity_penalty_usd_per_dmt,
                "Net shipment value USD": result.net_value_usd,
                "Value per dmt USD": result.value_per_dmt_usd,
            }
        )
    return pd.DataFrame(rows)
