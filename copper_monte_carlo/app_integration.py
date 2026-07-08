"""Streamlit integration for the Copper Monte Carlo Risk page."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from copper_monte_carlo.config import (
    config_from_assumptions,
    load_default_assumptions,
    validate_assumptions,
)
from copper_monte_carlo.plots import (
    copper_fan_chart,
    copper_spider_plot,
    final_distribution,
    margin_fan_chart,
)
from copper_monte_carlo.simulation_engine import paths_to_frame, run_monte_carlo


TRADE_MODE_LABELS = {
    "Concentrate merchant": "concentrate_merchant",
    "Smelter conversion": "smelter_conversion",
    "Refined copper trade": "refined_copper_trade",
    "Integrated conversion": "integrated_conversion",
}

TRADE_MODE_DESCRIPTIONS = {
    "concentrate_merchant": (
        "Buy concentrate from a producer and sell concentrate to a smelter. "
        "Margin comes from payable value, TC/RC term movement, logistics, "
        "financing, and hedge effects."
    ),
    "smelter_conversion": (
        "Buy concentrate, process it, and sell recovered refined copper. "
        "This uses recovery and processing-cost assumptions."
    ),
    "refined_copper_trade": (
        "Buy refined copper and sell it onward. Concentrate quality and TC/RC "
        "are not the economic drivers in this mode."
    ),
    "integrated_conversion": (
        "The original prototype chain: buy concentrate exposure, carry it, "
        "and sell payable copper equivalent."
    ),
}

SCENARIO_LABELS = {
    "base_case": "Base case",
    "bull_copper_tight_concentrate": "Bull copper / tight concentrate",
    "bear_copper_weak_demand": "Bear copper / weak demand",
    "high_freight_shock": "High freight shock",
    "negative_tcrc_stress": "Negative TC/RC stress",
    "unhedged_case": "Unhedged case",
    "half_hedged_case": "50% hedged case",
    "fully_hedged_case": "Fully hedged case",
    "dirty_concentrate_case": "Dirty concentrate case",
    "clean_concentrate_case": "Clean concentrate case",
}


def _metadata_table(assumptions: dict) -> pd.DataFrame:
    rows = []
    for name, meta in assumptions["metadata"]["input_sources"].items():
        rows.append(
            {
                "Input": name,
                "Value": meta["value"],
                "Source": meta["source"],
                "Comment": meta["comment"],
            }
        )
    return pd.DataFrame(rows)


def _static_values_table(values: dict[str, float]) -> pd.DataFrame:
    rows = [
        ("Dry metric tonnes", values["dry_metric_tonnes"], "dmt"),
        ("Contained copper", values["contained_copper_tonnes"], "tonnes Cu"),
        ("Payable copper", values["payable_copper_tonnes"], "tonnes Cu"),
        ("By-product credit", values["byproduct_credit_usd"], "USD"),
    ]
    return pd.DataFrame(
        [
            {
                "Metric": metric,
                "Value": f"{value:,.2f}",
                "Unit": unit,
                "Meaning": (
                    "Static cargo quantity or credit used in every simulated path."
                ),
            }
            for metric, value, unit in rows
        ]
    )


def _render_html_table(df: pd.DataFrame) -> None:
    """Render tables without Streamlit's pyarrow-backed dataframe element."""

    st.markdown(
        df.to_html(index=False, escape=True, classes="dashboard-table"),
        unsafe_allow_html=True,
    )


def render_monte_carlo_page() -> None:
    """Render the Monte Carlo page inside the existing Streamlit app."""

    assumptions = load_default_assumptions()
    st.title("Copper Market Risk Simulation")
    st.warning(assumptions["metadata"]["data_warning"])
    st.info(
        "Workflow: choose the physical trade structure, select a market scenario, "
        "then adjust the assumptions. The charts show simulated path outcomes and "
        "revalued margins, not realized accounting P&L."
    )

    scenario_names = list(assumptions["scenarios"].keys())
    scenario_options = {
        SCENARIO_LABELS.get(name, name.replace("_", " ").title()): name
        for name in scenario_names
    }
    with st.sidebar:
        st.header("Trade Structure")
        trade_mode_label = st.selectbox(
            "Trade mode",
            list(TRADE_MODE_LABELS.keys()),
            index=0,
        )
        trade_mode = TRADE_MODE_LABELS[trade_mode_label]
        st.caption(TRADE_MODE_DESCRIPTIONS[trade_mode])

        st.header("Market Scenario")
        scenario_label = st.selectbox(
            "Scenario preset",
            list(scenario_options.keys()),
            index=0,
        )
        scenario = scenario_options[scenario_label]
        st.caption(
            "Scenario presets override selected market assumptions such as drift, "
            "volatility, TC/RC, freight, hedge ratio, or financing rate."
        )

        st.header("Simulation Controls")
        n_simulations = st.number_input("Simulation paths", 100, 100000, 10000, 500)
        horizon_months = st.selectbox("Horizon months", [12, 24, 36], index=1)
        random_seed = st.number_input("Random seed", 0, 999999, 42, 1)

        with st.expander("1. Market Path Assumptions", expanded=True):
            initial_price = st.number_input("Initial copper price (USD/t)", 0.0, 50000.0, 12000.0, 50.0)
            annual_drift = st.number_input("Annual copper drift", -1.0, 1.0, 0.03, 0.01, format="%.4f")
            annual_volatility = st.number_input("Annual copper volatility", 0.0, 2.0, 0.24, 0.01, format="%.4f")
            tc_initial = st.number_input("Initial TC USD/dmt", -200.0, 300.0, -40.0, 1.0)
            tc_mean = st.number_input("Long-term TC mean USD/dmt", -200.0, 300.0, 45.0, 1.0)
            tc_vol = st.number_input("TC monthly volatility USD/dmt", 0.0, 100.0, 12.0, 1.0)
            rc_initial = st.number_input("Initial RC USD/lb", -0.20, 0.30, -0.04, 0.005, format="%.4f")
            rc_mean = st.number_input("Long-term RC mean USD/lb", -0.20, 0.30, 0.045, 0.005, format="%.4f")
            rc_vol = st.number_input("RC monthly volatility USD/lb", 0.0, 0.10, 0.012, 0.001, format="%.4f")
            freight_initial = st.number_input("Freight USD/wmt", 0.0, 250.0, 45.0, 1.0)
            freight_vol = st.number_input("Freight monthly volatility USD/wmt", 0.0, 100.0, 8.0, 1.0)

        with st.expander("2. Concentrate Quality"):
            wet_tonnes = st.number_input("Wet tonnes", 0.0, 1000000.0, 10000.0, 100.0)
            moisture = st.slider("Moisture fraction", 0.0, 0.20, 0.08, 0.005)
            copper_grade = st.slider("Copper grade fraction", 0.0, 0.60, 0.26, 0.005)
            payable = st.slider("Payable copper fraction", 0.0, 1.0, 0.965, 0.005)

        with st.expander("3. Logistics, Financing and Hedging"):
            storage_duration = st.number_input("Storage duration months", 0.0, 24.0, 2.0, 0.5)
            financing_rate = st.number_input("All-in financing rate fraction", 0.0, 1.0, 0.07, 0.005, format="%.4f")
            hedge_enabled = st.checkbox("Hedge enabled", True)
            hedge_ratio = st.slider("Hedge ratio", 0.0, 1.0, 0.80, 0.05)

        with st.expander("4. Trade-Mode Economics"):
            purchase_percentage = st.number_input(
                "Purchase payable value percentage",
                0.0,
                1.5,
                0.98,
                0.01,
                format="%.4f",
            )
            refined_purchase_premium = st.number_input(
                "Refined purchase premium USD/t",
                -500.0,
                1000.0,
                50.0,
                10.0,
            )
            refined_sale_premium = st.number_input(
                "Refined sale premium USD/t",
                -500.0,
                1000.0,
                100.0,
                10.0,
            )
            smelter_recovery = st.number_input(
                "Smelter recovery rate",
                0.0,
                1.0,
                0.985,
                0.005,
                format="%.4f",
            )
            processing_cost = st.number_input(
                "Smelting/refining cost USD/dmt",
                0.0,
                1000.0,
                120.0,
                5.0,
            )

    scenario_overrides = assumptions["scenarios"].get(scenario, {})
    overrides = {
        "n_simulations": int(n_simulations),
        "horizon_months": int(horizon_months),
        "random_seed": int(random_seed),
        "scenario_name": scenario,
        "trade_mode": trade_mode,
        "purchase_payable_value_percentage": purchase_percentage,
        "refined_copper_purchase_premium_usd_per_tonne": refined_purchase_premium,
        "refined_copper_sale_premium_usd_per_tonne": refined_sale_premium,
        "smelter_recovery_rate": smelter_recovery,
        "smelting_refining_cost_usd_per_dmt": processing_cost,
        "initial_copper_price_usd_per_tonne": scenario_overrides.get("copper_initial_price", initial_price),
        "annual_drift": scenario_overrides.get("copper_annual_drift", annual_drift),
        "annual_volatility": scenario_overrides.get("copper_annual_volatility", annual_volatility),
        "initial_tc_usd_per_dmt": scenario_overrides.get("tc_initial", tc_initial),
        "tc_mean_reversion_level": scenario_overrides.get("tc_mean_reversion_level", tc_mean),
        "tc_volatility": tc_vol,
        "initial_rc_usd_per_lb": scenario_overrides.get("rc_initial", rc_initial),
        "rc_mean_reversion_level": scenario_overrides.get("rc_mean_reversion_level", rc_mean),
        "rc_volatility": rc_vol,
        "initial_freight_usd_per_wmt": scenario_overrides.get("freight_initial", freight_initial),
        "freight_volatility": freight_vol,
        "wet_metric_tonnes": wet_tonnes,
        "moisture_percentage": moisture,
        "copper_grade_percentage": copper_grade,
        "payable_copper_percentage": payable,
        "storage_duration_months": storage_duration,
        "all_in_financing_rate": scenario_overrides.get("financing_rate", financing_rate),
        "hedge_enabled": scenario_overrides.get("hedge_enabled", hedge_enabled),
        "hedge_ratio": scenario_overrides.get("hedge_ratio", hedge_ratio),
    }
    config = config_from_assumptions(assumptions, **overrides)
    warnings = validate_assumptions(config)
    for warning in warnings:
        st.caption(f"Warning: {warning}")

    result = run_monte_carlo(config)
    kpis = result.risk_summary.set_index("Metric")["Value"]
    cols = st.columns(4)
    cols[0].metric("Expected final copper price", f"USD {kpis['Expected final copper price']:,.0f}/t")
    cols[1].metric("Expected margin", f"USD {kpis['Expected margin']:,.0f}")
    cols[2].metric("Probability of loss", f"{kpis['Probability of loss']:.1%}")
    cols[3].metric("95% VaR", f"USD {kpis['95% VaR']:,.0f}")
    st.caption(
        f"Trade mode: {trade_mode_label}. Market scenario: {scenario_label}. "
        f"{TRADE_MODE_DESCRIPTIONS[trade_mode]}"
    )

    tabs = st.tabs(
        [
            "Setup",
            "Copper Price Paths",
            "Margin Risk",
            "Risk Summary",
            "Export",
        ]
    )
    with tabs[0]:
        st.subheader("Simulation Setup")
        st.caption(
            "This summarizes the active model case after scenario presets have "
            "been applied."
        )
        setup = pd.DataFrame(
            [
                ("Trade mode", trade_mode_label),
                ("Market scenario", scenario_label),
                ("Simulations", f"{int(n_simulations):,}"),
                ("Horizon", f"{int(horizon_months)} months"),
                ("Random seed", str(int(random_seed))),
                ("Hedge", "Enabled" if config.hedge_enabled else "Disabled"),
                ("Hedge ratio", f"{config.hedge_ratio:.0%}"),
            ],
            columns=["Item", "Selected value"],
        )
        _render_html_table(setup)
        st.subheader("Input Sources")
        st.caption("Source notes for the default assumptions used by this page.")
        _render_html_table(_metadata_table(assumptions))

    with tabs[1]:
        st.caption(
            "Sampled paths show individual simulated copper outcomes; percentile "
            "charts summarize the central range across all paths."
        )
        st.plotly_chart(copper_spider_plot(result), use_container_width=True)
        st.plotly_chart(copper_fan_chart(result), use_container_width=True)
        st.plotly_chart(
            final_distribution(
                result.copper_price_paths[:, -1],
                "Final-Month Copper Price Distribution",
                "Copper price (USD/t)",
            ),
            use_container_width=True,
        )
    with tabs[2]:
        st.caption(
            "The margin fan chart revalues the selected trade at each simulated "
            "month using that month's copper price, TC/RC, freight, basis and "
            "hedge PnL. It is a mark-to-model path, not a cumulative monthly "
            "cash-flow curve. Its shape is mainly driven by copper price moves, "
            "hedge offset, TC/RC mean reversion, freight shocks, and fixed carry "
            "costs applied to the selected trade structure."
        )
        st.plotly_chart(margin_fan_chart(result), use_container_width=True)
        st.plotly_chart(
            final_distribution(
                result.margin_paths[:, -1],
                "Final-Month Margin Distribution",
                "Margin (USD)",
            ),
            use_container_width=True,
        )
    with tabs[3]:
        summary = result.risk_summary.copy()
        summary["Value"] = summary["Value"].map(lambda value: f"{value:,.4f}" if abs(value) < 10 else f"{value:,.0f}")
        _render_html_table(summary)
        st.subheader("Cargo Quantity Context")
        st.caption(
            "These values are not additional risk metrics. They are static cargo "
            "quantities and by-product credit used by the margin calculation."
        )
        _render_html_table(_static_values_table(result.static_values))
    with tabs[4]:
        price_paths = paths_to_frame(result.copper_price_paths, "copper_price_usd_per_tonne")
        margin_paths_frame = paths_to_frame(result.margin_paths, "margin_usd")
        st.download_button(
            "Download copper paths CSV",
            price_paths.to_csv(index=False),
            "simulated_copper_price_paths.csv",
            "text/csv",
        )
        st.download_button(
            "Download margin paths CSV",
            margin_paths_frame.to_csv(index=False),
            "simulated_margin_paths.csv",
            "text/csv",
        )
        st.download_button(
            "Download risk summary CSV",
            result.risk_summary.to_csv(index=False),
            "risk_summary.csv",
            "text/csv",
        )
