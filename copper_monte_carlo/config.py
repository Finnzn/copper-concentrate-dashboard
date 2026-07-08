"""Configuration loading and validation for copper Monte Carlo simulations."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import yaml


PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_ASSUMPTIONS_PATH = PACKAGE_DIR / "data" / "default_assumptions.yaml"


@dataclass
class MonteCarloConfig:
    """Flattened simulation settings used by the engine."""

    n_simulations: int = 10000
    horizon_months: int = 24
    random_seed: int = 42
    confidence_levels: tuple[float, ...] = (0.05, 0.10, 0.50, 0.90, 0.95)
    start_date: str = "today"
    scenario_name: str = "Base fallback case"
    trade_mode: str = "concentrate_merchant"
    purchase_payable_value_percentage: float = 0.98
    refined_copper_purchase_premium_usd_per_tonne: float = 50.0
    refined_copper_sale_premium_usd_per_tonne: float = 100.0
    smelter_recovery_rate: float = 0.985
    smelting_refining_cost_usd_per_dmt: float = 120.0
    initial_copper_price_usd_per_tonne: float = 12000.0
    annual_drift: float = 0.03
    annual_volatility: float = 0.24
    min_price_floor: float = 4000.0
    max_price_cap: float | None = None
    copper_jump_probability: float = 0.03
    copper_jump_mean: float = 0.0
    copper_jump_volatility: float = 0.08
    initial_tc_usd_per_dmt: float = -40.0
    tc_mean_reversion_level: float = 45.0
    tc_mean_reversion_speed: float = 0.12
    tc_volatility: float = 12.0
    tc_floor: float | None = -100.0
    tc_cap: float | None = 150.0
    initial_rc_usd_per_lb: float = -0.04
    rc_mean_reversion_level: float = 0.045
    rc_mean_reversion_speed: float = 0.12
    rc_volatility: float = 0.012
    rc_floor: float | None = -0.10
    rc_cap: float | None = 0.15
    initial_freight_usd_per_wmt: float = 45.0
    freight_mean_reversion_level: float = 40.0
    freight_mean_reversion_speed: float = 0.20
    freight_volatility: float = 8.0
    freight_jump_probability: float = 0.04
    freight_jump_size_mean: float = 15.0
    freight_jump_size_volatility: float = 10.0
    initial_basis_usd_per_tonne: float = 50.0
    basis_mean_reversion_level: float = 0.0
    basis_mean_reversion_speed: float = 0.35
    basis_volatility: float = 120.0
    initial_fx_rate: float = 1.0
    fx_drift: float = 0.0
    fx_volatility: float = 0.08
    wet_metric_tonnes: float = 10000.0
    moisture_percentage: float = 0.08
    copper_grade_percentage: float = 0.26
    payable_copper_percentage: float = 0.965
    gold_grade_g_per_tonne: float = 1.0
    silver_grade_g_per_tonne: float = 80.0
    gold_payability_percentage: float = 0.95
    silver_payability_percentage: float = 0.90
    gold_price_usd_per_oz: float = 3300.0
    silver_price_usd_per_oz: float = 40.0
    storage_cost_usd_per_tonne_per_month: float = 6.0
    storage_duration_months: float = 2.0
    insurance_rate_percentage_of_cargo_value: float = 0.0025
    port_handling_cost_usd_per_tonne: float = 8.0
    inland_transport_cost_usd_per_tonne: float = 15.0
    purchase_payment_timing_days: float = 5.0
    sale_payment_timing_days: float = 45.0
    shipping_duration_days: float = 35.0
    all_in_financing_rate: float = 0.07
    hedge_enabled: bool = True
    hedge_ratio: float = 0.80
    hedge_slippage_usd_per_tonne: float = 10.0
    hedge_transaction_cost_usd: float = 20.0
    loss_threshold_usd: float = 0.0
    high_copper_threshold_usd_per_tonne: float = 14000.0
    low_copper_threshold_usd_per_tonne: float = 9000.0
    correlation_matrix: np.ndarray = field(default_factory=lambda: np.eye(6))
    correlation_variables: tuple[str, ...] = (
        "copper_price",
        "tc",
        "rc",
        "freight",
        "fx",
        "basis",
    )

    @property
    def monthly_drift(self) -> float:
        return (1 + self.annual_drift) ** (1 / 12) - 1

    @property
    def monthly_volatility(self) -> float:
        return self.annual_volatility / np.sqrt(12)

    @property
    def working_capital_days(self) -> float:
        return (
            self.sale_payment_timing_days
            - self.purchase_payment_timing_days
            + self.shipping_duration_days
            + self.storage_duration_months * 30
        )


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    return data or {}


def _source_metadata(assumptions: dict[str, Any]) -> dict[str, dict[str, str]]:
    rows = {
        "Copper price": (
            assumptions["copper_price"]["initial_copper_price_usd_per_tonne"],
            "Replace with FRED, Yahoo, LME, or project price data when available.",
        ),
        "TC": (
            assumptions["tcrc"]["treatment_charge_usd_per_dmt_concentrate"],
            "Represents tight concentrate market fallback.",
        ),
        "RC": (
            assumptions["tcrc"]["refining_charge_usd_per_lb_payable_copper"],
            "USD/lb fallback, not cents/lb.",
        ),
        "Freight": (
            assumptions["logistics"]["freight_usd_per_wmt"],
            "Generic route estimate.",
        ),
        "Copper grade": (
            assumptions["concentrate_quality"]["copper_grade_percentage"],
            "Base-spec concentrate fallback.",
        ),
        "Hedge ratio": (
            assumptions["hedging"]["hedge_ratio"],
            "Editable hedge assumption.",
        ),
        "Trade mode": (
            assumptions.get("trade_model", {}).get(
                "trade_mode", "concentrate_merchant"
            ),
            "Selects which physical business model is simulated.",
        ),
    }
    return {
        name: {
            "value": str(value),
            "source": "fallback_assumption",
            "comment": comment,
        }
        for name, (value, comment) in rows.items()
    }


def load_default_assumptions(path: Path | None = None) -> dict[str, Any]:
    """Load fallback assumptions and attach transparent source metadata."""

    assumptions_path = path or DEFAULT_ASSUMPTIONS_PATH
    assumptions = _read_yaml(assumptions_path)
    assumptions["metadata"] = {
        "loaded_from": str(assumptions_path),
        "loaded_on": date.today().isoformat(),
        "data_warning": (
            "Using fallback assumptions. These are pragmatic placeholders, "
            "not official market data."
        ),
        "input_sources": _source_metadata(assumptions),
    }
    return assumptions


def config_from_assumptions(
    assumptions: dict[str, Any] | None = None, **overrides: Any
) -> MonteCarloConfig:
    """Create a flattened engine config from nested fallback assumptions."""

    data = assumptions or load_default_assumptions()
    sim = data["simulation_control"]
    trade_model = data.get("trade_model", {})
    copper = data["copper_price"]
    tcrc = data["tcrc"]
    logistics = data["logistics"]
    basis = data["basis"]
    fx = data["fx"]
    quality = data["concentrate_quality"]
    storage = data["storage_inventory"]
    financing = data["financing"]
    hedging = data["hedging"]
    risk = data["risk"]
    corr = data["correlation"]

    values: dict[str, Any] = {
        "n_simulations": int(sim["n_simulations"]),
        "horizon_months": int(sim["horizon_months"]),
        "random_seed": int(sim["random_seed"]),
        "confidence_levels": tuple(float(x) for x in sim["confidence_levels"]),
        "start_date": str(sim["start_date"]),
        "scenario_name": str(sim["scenario_name"]),
        "trade_mode": str(trade_model.get("trade_mode", "concentrate_merchant")),
        "purchase_payable_value_percentage": float(
            trade_model.get("purchase_payable_value_percentage", 0.98)
        ),
        "refined_copper_purchase_premium_usd_per_tonne": float(
            trade_model.get("refined_copper_purchase_premium_usd_per_tonne", 50)
        ),
        "refined_copper_sale_premium_usd_per_tonne": float(
            trade_model.get("refined_copper_sale_premium_usd_per_tonne", 100)
        ),
        "smelter_recovery_rate": float(trade_model.get("smelter_recovery_rate", 0.985)),
        "smelting_refining_cost_usd_per_dmt": float(
            trade_model.get("smelting_refining_cost_usd_per_dmt", 120)
        ),
        "initial_copper_price_usd_per_tonne": float(
            copper["initial_copper_price_usd_per_tonne"]
        ),
        "annual_drift": float(copper["annual_drift"]),
        "annual_volatility": float(copper["annual_volatility"]),
        "min_price_floor": float(copper["min_price_floor"]),
        "max_price_cap": copper["max_price_cap"],
        "copper_jump_probability": float(copper["jump_probability"]),
        "copper_jump_mean": float(copper["jump_mean"]),
        "copper_jump_volatility": float(copper["jump_volatility"]),
        "initial_tc_usd_per_dmt": float(
            tcrc["treatment_charge_usd_per_dmt_concentrate"]
        ),
        "tc_mean_reversion_level": float(tcrc["tc_mean_reversion_level"]),
        "tc_mean_reversion_speed": float(tcrc["tc_mean_reversion_speed"]),
        "tc_volatility": float(tcrc["tc_volatility"]),
        "tc_floor": tcrc["tc_floor"],
        "tc_cap": tcrc["tc_cap"],
        "initial_rc_usd_per_lb": float(
            tcrc["refining_charge_usd_per_lb_payable_copper"]
        ),
        "rc_mean_reversion_level": float(tcrc["rc_mean_reversion_level"]),
        "rc_mean_reversion_speed": float(tcrc["rc_mean_reversion_speed"]),
        "rc_volatility": float(tcrc["rc_volatility"]),
        "rc_floor": tcrc["rc_floor"],
        "rc_cap": tcrc["rc_cap"],
        "initial_freight_usd_per_wmt": float(logistics["freight_usd_per_wmt"]),
        "freight_mean_reversion_level": float(
            logistics["freight_mean_reversion_level"]
        ),
        "freight_mean_reversion_speed": float(
            logistics["freight_mean_reversion_speed"]
        ),
        "freight_volatility": float(logistics["freight_volatility"]),
        "freight_jump_probability": float(logistics["freight_jump_probability"]),
        "freight_jump_size_mean": float(logistics["freight_jump_size_mean"]),
        "freight_jump_size_volatility": float(
            logistics["freight_jump_size_volatility"]
        ),
        "initial_basis_usd_per_tonne": float(
            basis["initial_basis_spread_usd_per_tonne"]
        ),
        "basis_mean_reversion_level": float(basis["basis_mean_reversion_level"]),
        "basis_mean_reversion_speed": float(basis["basis_mean_reversion_speed"]),
        "basis_volatility": float(basis["basis_volatility"]),
        "initial_fx_rate": 1.0,
        "fx_drift": float(fx["fx_drift"]),
        "fx_volatility": float(fx["fx_volatility"]),
        "wet_metric_tonnes": float(quality["wet_metric_tonnes"]),
        "moisture_percentage": float(quality["moisture_percentage"]),
        "copper_grade_percentage": float(quality["copper_grade_percentage"]),
        "payable_copper_percentage": float(quality["payable_copper_percentage"]),
        "gold_grade_g_per_tonne": float(quality["gold_grade_g_per_tonne"]),
        "silver_grade_g_per_tonne": float(quality["silver_grade_g_per_tonne"]),
        "gold_payability_percentage": float(quality["gold_payability_percentage"]),
        "silver_payability_percentage": float(
            quality["silver_payability_percentage"]
        ),
        "gold_price_usd_per_oz": float(quality["gold_price_usd_per_oz"]),
        "silver_price_usd_per_oz": float(quality["silver_price_usd_per_oz"]),
        "storage_cost_usd_per_tonne_per_month": float(
            storage["storage_cost_usd_per_tonne_per_month"]
        ),
        "storage_duration_months": float(storage["storage_duration_months"]),
        "insurance_rate_percentage_of_cargo_value": float(
            logistics["insurance_rate_percentage_of_cargo_value"]
        ),
        "port_handling_cost_usd_per_tonne": float(
            logistics["port_handling_cost_usd_per_tonne"]
        ),
        "inland_transport_cost_usd_per_tonne": float(
            logistics["inland_transport_cost_usd_per_tonne"]
        ),
        "purchase_payment_timing_days": float(
            financing["purchase_payment_timing_days"]
        ),
        "sale_payment_timing_days": float(financing["sale_payment_timing_days"]),
        "shipping_duration_days": float(logistics["shipping_duration_days"]),
        "all_in_financing_rate": float(
            financing["usd_interest_rate"] + financing["credit_spread"]
        ),
        "hedge_enabled": bool(hedging["hedge_enabled"]),
        "hedge_ratio": float(hedging["hedge_ratio"]),
        "hedge_slippage_usd_per_tonne": float(hedging["hedge_slippage"]),
        "hedge_transaction_cost_usd": float(hedging["hedge_transaction_cost"]),
        "loss_threshold_usd": float(risk["loss_threshold_usd"]),
        "high_copper_threshold_usd_per_tonne": float(
            risk["high_copper_threshold_usd_per_tonne"]
        ),
        "low_copper_threshold_usd_per_tonne": float(
            risk["low_copper_threshold_usd_per_tonne"]
        ),
        "correlation_variables": tuple(corr["variables"]),
        "correlation_matrix": np.array(corr["matrix"], dtype=float),
    }
    values.update(overrides)
    return MonteCarloConfig(**values)


def validate_assumptions(config: MonteCarloConfig) -> list[str]:
    """Return validation warnings for questionable assumptions."""

    warnings: list[str] = []
    if config.n_simulations < 1000:
        warnings.append("n_simulations is very small; results may be unstable.")
    if config.initial_copper_price_usd_per_tonne < 4000:
        warnings.append("Copper price is below 4,000 USD/t.")
    if config.initial_copper_price_usd_per_tonne > 25000:
        warnings.append("Copper price is above 25,000 USD/t.")
    if not 0.10 <= config.copper_grade_percentage <= 0.45:
        warnings.append("Copper grade is outside the 10% to 45% validation range.")
    if not 0 <= config.moisture_percentage <= 0.15:
        warnings.append("Moisture is outside the 0% to 15% validation range.")
    if config.payable_copper_percentage > 1:
        warnings.append("Payable copper should be expressed as a decimal <= 1.")
    if config.initial_freight_usd_per_wmt < 0:
        warnings.append("Freight cannot be negative.")
    if config.all_in_financing_rate < 0:
        warnings.append("Financing rate cannot be negative.")
    if not 0 <= config.hedge_ratio <= 1:
        warnings.append("Hedge ratio must be between 0 and 1.")
    if config.trade_mode not in {
        "concentrate_merchant",
        "smelter_conversion",
        "refined_copper_trade",
        "integrated_conversion",
    }:
        warnings.append(f"Unknown trade mode: {config.trade_mode}.")
    eigenvalues = np.linalg.eigvalsh(config.correlation_matrix)
    if eigenvalues.min() < -1e-8:
        warnings.append("Correlation matrix is not positive semi-definite.")
    warnings.append(
        "Fallback assumptions are active unless overridden by user input or CSV data."
    )
    return warnings
