"""Core valuation formulas for copper concentrate shipments.

The functions in this module intentionally keep the commercial formulas
transparent. The model is simplified and educational, but the unit handling is
made explicit because concentrate valuation mixes USD/dmt and US cents/lb.
"""

from __future__ import annotations

from dataclasses import dataclass


LB_PER_METRIC_TONNE = 2204.62262


@dataclass(frozen=True)
class ConcentrateAssumptions:
    """Commercial and technical assumptions for one concentrate shipment."""

    wet_metric_tonnes: float
    moisture_percentage: float
    copper_grade_percentage: float
    payable_copper_percentage: float
    lme_copper_price_usd_per_tonne: float
    tc_usd_per_dmt: float
    rc_cents_per_lb: float
    freight_usd_per_dmt: float
    impurity_penalty_usd_per_dmt: float
    byproduct_credit_usd_per_dmt: float = 0.0
    fx_rate_usd_to_chf: float = 0.90


@dataclass(frozen=True)
class ValuationResult:
    """Calculated shipment economics."""

    dry_metric_tonnes: float
    contained_copper_tonnes: float
    payable_copper_tonnes: float
    payable_copper_lb: float
    gross_copper_value_usd: float
    treatment_charge_usd: float
    refining_charge_usd: float
    freight_cost_usd: float
    impurity_penalty_usd: float
    byproduct_credit_usd: float
    total_deductions_usd: float
    net_value_usd: float
    value_per_dmt_usd: float
    net_value_chf: float


def clamp_percentage(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    """Keep percentage inputs inside a sensible range."""

    return max(lower, min(upper, value))


def calculate_valuation(assumptions: ConcentrateAssumptions) -> ValuationResult:
    """Calculate simplified copper concentrate shipment value.

    Formula sequence:
    1. Convert wet metric tonnes into dry metric tonnes using moisture.
    2. Calculate contained and payable copper.
    3. Value payable copper using an LME copper price.
    4. Deduct TC, RC, freight, and impurity penalties.
    5. Add any by-product credits.
    """

    wet_metric_tonnes = max(0.0, assumptions.wet_metric_tonnes)
    moisture_percentage = clamp_percentage(assumptions.moisture_percentage)
    copper_grade_percentage = clamp_percentage(assumptions.copper_grade_percentage)
    payable_copper_percentage = clamp_percentage(assumptions.payable_copper_percentage)

    dry_metric_tonnes = wet_metric_tonnes * (1 - moisture_percentage / 100)
    contained_copper_tonnes = dry_metric_tonnes * copper_grade_percentage / 100
    payable_copper_tonnes = contained_copper_tonnes * payable_copper_percentage / 100
    payable_copper_lb = payable_copper_tonnes * LB_PER_METRIC_TONNE

    gross_copper_value_usd = (
        payable_copper_tonnes * assumptions.lme_copper_price_usd_per_tonne
    )
    treatment_charge_usd = dry_metric_tonnes * assumptions.tc_usd_per_dmt
    refining_charge_usd = payable_copper_lb * assumptions.rc_cents_per_lb / 100
    freight_cost_usd = dry_metric_tonnes * assumptions.freight_usd_per_dmt
    impurity_penalty_usd = dry_metric_tonnes * assumptions.impurity_penalty_usd_per_dmt
    byproduct_credit_usd = dry_metric_tonnes * assumptions.byproduct_credit_usd_per_dmt

    total_deductions_usd = (
        treatment_charge_usd
        + refining_charge_usd
        + freight_cost_usd
        + impurity_penalty_usd
    )
    net_value_usd = (
        gross_copper_value_usd - total_deductions_usd + byproduct_credit_usd
    )
    value_per_dmt_usd = (
        net_value_usd / dry_metric_tonnes if dry_metric_tonnes > 0 else 0.0
    )
    net_value_chf = net_value_usd * assumptions.fx_rate_usd_to_chf

    return ValuationResult(
        dry_metric_tonnes=dry_metric_tonnes,
        contained_copper_tonnes=contained_copper_tonnes,
        payable_copper_tonnes=payable_copper_tonnes,
        payable_copper_lb=payable_copper_lb,
        gross_copper_value_usd=gross_copper_value_usd,
        treatment_charge_usd=treatment_charge_usd,
        refining_charge_usd=refining_charge_usd,
        freight_cost_usd=freight_cost_usd,
        impurity_penalty_usd=impurity_penalty_usd,
        byproduct_credit_usd=byproduct_credit_usd,
        total_deductions_usd=total_deductions_usd,
        net_value_usd=net_value_usd,
        value_per_dmt_usd=value_per_dmt_usd,
        net_value_chf=net_value_chf,
    )


def valuation_bridge(result: ValuationResult) -> dict[str, float]:
    """Return a waterfall-style bridge for charting shipment value."""

    return {
        "Gross copper value": result.gross_copper_value_usd,
        "Treatment charge deduction": -result.treatment_charge_usd,
        "Refining charge deduction": -result.refining_charge_usd,
        "Freight deduction": -result.freight_cost_usd,
        "Impurity penalty deduction": -result.impurity_penalty_usd,
        "By-product credit": result.byproduct_credit_usd,
        "Net value": result.net_value_usd,
    }
