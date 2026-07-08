"""Vectorized physical copper concentrate economics for simulated paths."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from copper_monte_carlo.config import MonteCarloConfig


LB_PER_METRIC_TONNE = 2204.62262185
GRAMS_PER_TROY_OUNCE = 31.1034768


@dataclass(frozen=True)
class ConcentrateStaticValues:
    dry_metric_tonnes: float
    contained_copper_tonnes: float
    payable_copper_tonnes: float
    payable_copper_lbs: float
    byproduct_credit_usd: float


def static_concentrate_values(config: MonteCarloConfig) -> ConcentrateStaticValues:
    """Calculate quality-dependent cargo values that do not vary by path."""

    dry_metric_tonnes = config.wet_metric_tonnes * (1 - config.moisture_percentage)
    contained_copper_tonnes = dry_metric_tonnes * config.copper_grade_percentage
    payable_copper_tonnes = contained_copper_tonnes * config.payable_copper_percentage
    payable_copper_lbs = payable_copper_tonnes * LB_PER_METRIC_TONNE
    gold_oz = (
        dry_metric_tonnes
        * config.gold_grade_g_per_tonne
        / GRAMS_PER_TROY_OUNCE
        * config.gold_payability_percentage
    )
    silver_oz = (
        dry_metric_tonnes
        * config.silver_grade_g_per_tonne
        / GRAMS_PER_TROY_OUNCE
        * config.silver_payability_percentage
    )
    byproduct_credit_usd = (
        gold_oz * config.gold_price_usd_per_oz
        + silver_oz * config.silver_price_usd_per_oz
    )
    return ConcentrateStaticValues(
        dry_metric_tonnes=dry_metric_tonnes,
        contained_copper_tonnes=contained_copper_tonnes,
        payable_copper_tonnes=payable_copper_tonnes,
        payable_copper_lbs=payable_copper_lbs,
        byproduct_credit_usd=byproduct_credit_usd,
    )


def margin_paths(
    config: MonteCarloConfig,
    copper_price_paths: np.ndarray,
    tc_paths: np.ndarray,
    rc_paths: np.ndarray,
    freight_paths: np.ndarray,
    basis_paths: np.ndarray,
) -> dict[str, np.ndarray | float]:
    """Calculate cargo value, trader costs, hedge PnL, and net margin by path."""

    static = static_concentrate_values(config)
    gross_metal_value = static.payable_copper_tonnes * copper_price_paths
    treatment_charge_cost = static.dry_metric_tonnes * tc_paths
    refining_charge_cost = static.payable_copper_lbs * rc_paths
    freight_cost = config.wet_metric_tonnes * freight_paths
    storage_cost = (
        static.dry_metric_tonnes
        * config.storage_cost_usd_per_tonne_per_month
        * config.storage_duration_months
    )
    port_cost = config.wet_metric_tonnes * config.port_handling_cost_usd_per_tonne
    inland_cost = config.wet_metric_tonnes * config.inland_transport_cost_usd_per_tonne
    insurance_cost = gross_metal_value * config.insurance_rate_percentage_of_cargo_value
    financing_cost = (
        gross_metal_value
        * config.all_in_financing_rate
        * config.working_capital_days
        / 360
    )
    fixed_costs = (
        freight_cost
        + storage_cost
        + port_cost
        + inland_cost
        + insurance_cost
        + financing_cost
    )
    initial_gross_value = (
        static.payable_copper_tonnes * config.initial_copper_price_usd_per_tonne
    )
    initial_tc_value = static.dry_metric_tonnes * config.initial_tc_usd_per_dmt
    initial_rc_value = static.payable_copper_lbs * config.initial_rc_usd_per_lb
    initial_concentrate_invoice = (
        initial_gross_value
        * config.purchase_payable_value_percentage
        - initial_tc_value
        - initial_rc_value
        + static.byproduct_credit_usd
    )

    if config.trade_mode == "concentrate_merchant":
        sale_invoice = (
            gross_metal_value
            - treatment_charge_cost
            - refining_charge_cost
            + static.byproduct_credit_usd
        )
        unhedged_margin = sale_invoice - initial_concentrate_invoice - fixed_costs
    elif config.trade_mode == "smelter_conversion":
        refined_sale_value = (
            static.payable_copper_tonnes
            * config.smelter_recovery_rate
            * copper_price_paths
        )
        processing_cost = (
            static.dry_metric_tonnes * config.smelting_refining_cost_usd_per_dmt
        )
        unhedged_margin = (
            refined_sale_value
            + static.byproduct_credit_usd
            - initial_concentrate_invoice
            - processing_cost
            - fixed_costs
        )
    elif config.trade_mode == "refined_copper_trade":
        refined_tonnes = static.payable_copper_tonnes
        purchase_cost = refined_tonnes * (
            config.initial_copper_price_usd_per_tonne
            + config.refined_copper_purchase_premium_usd_per_tonne
        )
        sale_value = refined_tonnes * (
            copper_price_paths + config.refined_copper_sale_premium_usd_per_tonne
        )
        refined_freight_cost = refined_tonnes * freight_paths
        refined_fixed_costs = (
            refined_freight_cost
            + refined_tonnes
            * config.storage_cost_usd_per_tonne_per_month
            * config.storage_duration_months
            + sale_value * config.insurance_rate_percentage_of_cargo_value
            + sale_value
            * config.all_in_financing_rate
            * config.working_capital_days
            / 360
        )
        unhedged_margin = sale_value - purchase_cost - refined_fixed_costs
    else:
        purchase_cost = (
            static.payable_copper_tonnes
            * config.initial_copper_price_usd_per_tonne
            * config.purchase_payable_value_percentage
        )
        unhedged_margin = (
            gross_metal_value
            + static.byproduct_credit_usd
            - purchase_cost
            - treatment_charge_cost
            - refining_charge_cost
            - fixed_costs
        )
    hedge_ratio = config.hedge_ratio if config.hedge_enabled else 0.0
    initial_effective_price = (
        config.initial_copper_price_usd_per_tonne + config.initial_basis_usd_per_tonne
    )
    effective_price = copper_price_paths + basis_paths
    hedge_pnl = (
        hedge_ratio
        * static.payable_copper_tonnes
        * (initial_effective_price - effective_price)
    )
    hedge_cost = hedge_ratio * static.payable_copper_tonnes * (
        config.hedge_slippage_usd_per_tonne + config.hedge_transaction_cost_usd / 1000
    )
    hedged_margin = unhedged_margin + hedge_pnl - hedge_cost
    return {
        "gross_metal_value": gross_metal_value,
        "unhedged_margin": unhedged_margin,
        "hedge_pnl": hedge_pnl,
        "simulated_margin_paths": hedged_margin,
        "dry_metric_tonnes": static.dry_metric_tonnes,
        "contained_copper_tonnes": static.contained_copper_tonnes,
        "payable_copper_tonnes": static.payable_copper_tonnes,
        "byproduct_credit_usd": static.byproduct_credit_usd,
    }
