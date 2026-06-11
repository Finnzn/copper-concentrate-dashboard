"""Core valuation formulas for copper concentrate shipments.

The functions in this module intentionally keep the commercial formulas
transparent. The model is simplified and educational, but the unit handling is
made explicit because concentrate valuation mixes USD/dmt and US cents/lb.
"""

from __future__ import annotations

from dataclasses import dataclass


LB_PER_METRIC_TONNE = 2204.62262
GRAMS_PER_TROY_OUNCE = 31.1034768


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
    copper_payable_deduction_unit_percentage: float = 1.0
    gold_grade_g_per_dmt: float = 1.2
    gold_payable_percentage: float = 90.0
    gold_price_usd_per_oz: float = 2300.0
    gold_refining_charge_usd_per_oz: float = 8.0
    silver_grade_g_per_dmt: float = 35.0
    silver_payable_percentage: float = 90.0
    silver_price_usd_per_oz: float = 28.0
    silver_refining_charge_usd_per_oz: float = 0.45
    other_byproduct_credit_usd_per_dmt: float = 0.0
    arsenic_ppm: float = 1200.0
    bismuth_ppm: float = 150.0
    fluorine_ppm: float = 500.0
    financing_days: float = 45.0
    annual_financing_rate_percentage: float = 6.0
    fx_rate_usd_to_chf: float = 0.90


@dataclass(frozen=True)
class ValuationResult:
    """Calculated shipment economics."""

    dry_metric_tonnes: float
    contained_copper_tonnes: float
    payable_copper_by_percentage_tonnes: float
    payable_copper_by_deduction_tonnes: float
    payable_copper_tonnes: float
    payable_copper_lb: float
    gross_copper_value_usd: float
    treatment_charge_usd: float
    refining_charge_usd: float
    freight_cost_usd: float
    flat_impurity_penalty_usd: float
    arsenic_penalty_usd: float
    bismuth_penalty_usd: float
    fluorine_penalty_usd: float
    total_impurity_penalty_usd: float
    gold_payable_oz: float
    silver_payable_oz: float
    gold_credit_usd: float
    silver_credit_usd: float
    other_byproduct_credit_usd: float
    byproduct_credit_usd: float
    financing_cost_usd: float
    total_deductions_usd: float
    net_value_usd: float
    value_per_dmt_usd: float
    net_value_chf: float


def clamp_percentage(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    """Keep percentage inputs inside a sensible range."""

    return max(lower, min(upper, value))


def impurity_penalty_usd(
    dry_metric_tonnes: float,
    assay_ppm: float,
    threshold_ppm: float,
    penalty_usd_per_dmt_per_1000ppm: float,
) -> float:
    """Calculate a simple threshold-based impurity penalty."""

    excess_ppm = max(0.0, assay_ppm - threshold_ppm)
    return dry_metric_tonnes * (excess_ppm / 1000) * penalty_usd_per_dmt_per_1000ppm


def payable_ounces(
    dry_metric_tonnes: float, grade_g_per_dmt: float, payable_percentage: float
) -> float:
    """Convert precious metal grade into payable troy ounces."""

    contained_ounces = max(0.0, dry_metric_tonnes * grade_g_per_dmt) / GRAMS_PER_TROY_OUNCE
    return contained_ounces * clamp_percentage(payable_percentage) / 100


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
    copper_payable_deduction_unit_percentage = max(
        0.0, assumptions.copper_payable_deduction_unit_percentage
    )

    dry_metric_tonnes = wet_metric_tonnes * (1 - moisture_percentage / 100)
    contained_copper_tonnes = dry_metric_tonnes * copper_grade_percentage / 100
    payable_copper_by_percentage_tonnes = (
        contained_copper_tonnes * payable_copper_percentage / 100
    )
    payable_copper_by_deduction_tonnes = (
        dry_metric_tonnes
        * max(0.0, copper_grade_percentage - copper_payable_deduction_unit_percentage)
        / 100
    )
    payable_copper_tonnes = min(
        payable_copper_by_percentage_tonnes, payable_copper_by_deduction_tonnes
    )
    payable_copper_lb = payable_copper_tonnes * LB_PER_METRIC_TONNE

    gross_copper_value_usd = (
        payable_copper_tonnes * assumptions.lme_copper_price_usd_per_tonne
    )
    treatment_charge_usd = dry_metric_tonnes * assumptions.tc_usd_per_dmt
    refining_charge_usd = payable_copper_lb * assumptions.rc_cents_per_lb / 100
    freight_cost_usd = dry_metric_tonnes * assumptions.freight_usd_per_dmt
    flat_impurity_penalty_usd = (
        dry_metric_tonnes * assumptions.impurity_penalty_usd_per_dmt
    )
    arsenic_penalty_usd = impurity_penalty_usd(
        dry_metric_tonnes, assumptions.arsenic_ppm, 2000.0, 3.0
    )
    bismuth_penalty_usd = impurity_penalty_usd(
        dry_metric_tonnes, assumptions.bismuth_ppm, 500.0, 8.0
    )
    fluorine_penalty_usd = impurity_penalty_usd(
        dry_metric_tonnes, assumptions.fluorine_ppm, 1000.0, 6.0
    )
    total_impurity_penalty_usd = (
        flat_impurity_penalty_usd
        + arsenic_penalty_usd
        + bismuth_penalty_usd
        + fluorine_penalty_usd
    )

    gold_payable_oz = payable_ounces(
        dry_metric_tonnes,
        assumptions.gold_grade_g_per_dmt,
        assumptions.gold_payable_percentage,
    )
    silver_payable_oz = payable_ounces(
        dry_metric_tonnes,
        assumptions.silver_grade_g_per_dmt,
        assumptions.silver_payable_percentage,
    )
    gold_credit_usd = gold_payable_oz * (
        assumptions.gold_price_usd_per_oz - assumptions.gold_refining_charge_usd_per_oz
    )
    silver_credit_usd = silver_payable_oz * (
        assumptions.silver_price_usd_per_oz
        - assumptions.silver_refining_charge_usd_per_oz
    )
    other_byproduct_credit_usd = (
        dry_metric_tonnes * assumptions.other_byproduct_credit_usd_per_dmt
    )
    byproduct_credit_usd = (
        gold_credit_usd + silver_credit_usd + other_byproduct_credit_usd
    )

    subtotal_before_financing_usd = (
        gross_copper_value_usd
        - treatment_charge_usd
        - refining_charge_usd
        - freight_cost_usd
        - total_impurity_penalty_usd
        + byproduct_credit_usd
    )
    financing_cost_usd = max(0.0, subtotal_before_financing_usd) * (
        max(0.0, assumptions.annual_financing_rate_percentage) / 100
    ) * (max(0.0, assumptions.financing_days) / 360)
    total_deductions_usd = (
        treatment_charge_usd
        + refining_charge_usd
        + freight_cost_usd
        + total_impurity_penalty_usd
        + financing_cost_usd
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
        payable_copper_by_percentage_tonnes=payable_copper_by_percentage_tonnes,
        payable_copper_by_deduction_tonnes=payable_copper_by_deduction_tonnes,
        payable_copper_tonnes=payable_copper_tonnes,
        payable_copper_lb=payable_copper_lb,
        gross_copper_value_usd=gross_copper_value_usd,
        treatment_charge_usd=treatment_charge_usd,
        refining_charge_usd=refining_charge_usd,
        freight_cost_usd=freight_cost_usd,
        flat_impurity_penalty_usd=flat_impurity_penalty_usd,
        arsenic_penalty_usd=arsenic_penalty_usd,
        bismuth_penalty_usd=bismuth_penalty_usd,
        fluorine_penalty_usd=fluorine_penalty_usd,
        total_impurity_penalty_usd=total_impurity_penalty_usd,
        gold_payable_oz=gold_payable_oz,
        silver_payable_oz=silver_payable_oz,
        gold_credit_usd=gold_credit_usd,
        silver_credit_usd=silver_credit_usd,
        other_byproduct_credit_usd=other_byproduct_credit_usd,
        byproduct_credit_usd=byproduct_credit_usd,
        financing_cost_usd=financing_cost_usd,
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
        "Impurity penalty deduction": -result.total_impurity_penalty_usd,
        "By-product credit": result.byproduct_credit_usd,
        "Financing cost": -result.financing_cost_usd,
    }
