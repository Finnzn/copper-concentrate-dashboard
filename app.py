from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.risk import (
    charge_move_impact,
    copper_price_move_impact,
    largest_selected_risk_driver,
    sensitivity_heatmap,
)
from src.scenarios import build_scenarios
from src.valuation import ConcentrateAssumptions, calculate_valuation, valuation_bridge


DEFAULT_INPUTS = {
    "wet_metric_tonnes": 10_000.0,
    "moisture_percentage": 8.0,
    "copper_grade_percentage": 26.0,
    "payable_copper_percentage": 96.5,
    "lme_copper_price_usd_per_tonne": 9_500.0,
    "tc_usd_per_dmt": 80.0,
    "rc_cents_per_lb": 8.0,
    "freight_usd_per_dmt": 55.0,
    "impurity_penalty_usd_per_dmt": 12.0,
    "byproduct_credit_usd_per_dmt": 25.0,
    "fx_rate_usd_to_chf": 0.90,
}


st.set_page_config(
    page_title="Copper Concentrate Trade Economics Dashboard",
    page_icon="Cu",
    layout="wide",
)


def money(value: float) -> str:
    """Format USD values for compact dashboard display."""

    return f"${value:,.0f}"


def tonnes(value: float) -> str:
    return f"{value:,.2f} t"


def render_html_table(df: pd.DataFrame) -> None:
    """Render a small table without Streamlit's pyarrow-backed dataframe path."""

    st.markdown(
        """
        <style>
        .dashboard-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.92rem;
        }
        .dashboard-table th {
            background-color: #26323f;
            color: #ffffff;
            text-align: left;
            padding: 0.55rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.16);
        }
        .dashboard-table td {
            padding: 0.5rem 0.55rem;
            border-bottom: 1px solid rgba(128, 128, 128, 0.28);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        df.to_html(index=False, escape=True, classes="dashboard-table"),
        unsafe_allow_html=True,
    )


@st.cache_data
def load_sample_concentrates() -> pd.DataFrame:
    """Load illustrative concentrate profiles for quick scenario setup."""

    return pd.read_csv("data/sample_concentrate_specs.csv")


def initialize_sidebar_state() -> None:
    """Ensure sidebar widgets have stable defaults before they are rendered."""

    for key, value in DEFAULT_INPUTS.items():
        st.session_state.setdefault(key, value)
    st.session_state.setdefault("active_sample_concentrate", "Manual inputs")


def apply_sample_to_sidebar(sample: pd.Series) -> None:
    """Populate editable sidebar assumptions from a selected sample cargo."""

    sample_fields = [
        "wet_metric_tonnes",
        "moisture_percentage",
        "copper_grade_percentage",
        "payable_copper_percentage",
        "tc_usd_per_dmt",
        "rc_cents_per_lb",
        "freight_usd_per_dmt",
        "impurity_penalty_usd_per_dmt",
        "byproduct_credit_usd_per_dmt",
    ]
    for field in sample_fields:
        st.session_state[field] = float(sample[field])


def build_assumptions_from_sidebar() -> ConcentrateAssumptions:
    """Collect all user assumptions in the sidebar."""

    initialize_sidebar_state()
    sample_concentrates = load_sample_concentrates()
    sample_names = ["Manual inputs"] + sample_concentrates["concentrate_name"].tolist()

    st.sidebar.header("Sample Concentrate")
    selected_sample = st.sidebar.selectbox(
        "Load sample concentrate",
        sample_names,
        index=sample_names.index(st.session_state.active_sample_concentrate),
    )

    if selected_sample != st.session_state.active_sample_concentrate:
        st.session_state.active_sample_concentrate = selected_sample
        if selected_sample != "Manual inputs":
            selected_row = sample_concentrates.loc[
                sample_concentrates["concentrate_name"] == selected_sample
            ].iloc[0]
            apply_sample_to_sidebar(selected_row)
        st.rerun()

    if selected_sample != "Manual inputs":
        selected_row = sample_concentrates.loc[
            sample_concentrates["concentrate_name"] == selected_sample
        ].iloc[0]
        st.sidebar.caption(
            f"{selected_row['origin_region']} - {selected_row['commercial_note']}"
        )
    else:
        st.sidebar.caption("Build a cargo case from your own assumptions.")

    st.sidebar.header("Shipment Assumptions")
    wet_metric_tonnes = st.sidebar.number_input(
        "Shipment size, wet metric tonnes (wmt)",
        min_value=0.0,
        step=100.0,
        key="wet_metric_tonnes",
    )
    moisture_percentage = st.sidebar.slider(
        "Moisture percentage (%)",
        min_value=0.0,
        max_value=20.0,
        step=0.1,
        key="moisture_percentage",
    )
    copper_grade_percentage = st.sidebar.slider(
        "Copper grade (%)",
        min_value=0.0,
        max_value=60.0,
        step=0.1,
        key="copper_grade_percentage",
    )
    payable_copper_percentage = st.sidebar.slider(
        "Payable copper (%)",
        min_value=0.0,
        max_value=100.0,
        step=0.1,
        key="payable_copper_percentage",
    )

    st.sidebar.header("Commercial Terms")
    lme_copper_price_usd_per_tonne = st.sidebar.number_input(
        "LME copper price (USD per metric tonne)",
        min_value=0.0,
        step=50.0,
        key="lme_copper_price_usd_per_tonne",
    )
    tc_usd_per_dmt = st.sidebar.number_input(
        "Treatment charge, TC (USD/dmt)",
        min_value=0.0,
        step=1.0,
        key="tc_usd_per_dmt",
    )
    rc_cents_per_lb = st.sidebar.number_input(
        "Refining charge, RC (US¢/lb)",
        min_value=0.0,
        step=0.25,
        key="rc_cents_per_lb",
    )
    freight_usd_per_dmt = st.sidebar.number_input(
        "Freight/logistics cost (USD/dmt)",
        min_value=0.0,
        step=1.0,
        key="freight_usd_per_dmt",
    )
    impurity_penalty_usd_per_dmt = st.sidebar.number_input(
        "Impurity penalty (USD/dmt)",
        min_value=0.0,
        step=1.0,
        key="impurity_penalty_usd_per_dmt",
    )
    byproduct_credit_usd_per_dmt = st.sidebar.number_input(
        "Gold/silver by-product credit (USD/dmt)",
        min_value=0.0,
        step=1.0,
        key="byproduct_credit_usd_per_dmt",
    )
    fx_rate_usd_to_chf = st.sidebar.number_input(
        "Optional FX rate, USD to CHF",
        min_value=0.0,
        step=0.01,
        format="%.4f",
        key="fx_rate_usd_to_chf",
    )

    return ConcentrateAssumptions(
        wet_metric_tonnes=wet_metric_tonnes,
        moisture_percentage=moisture_percentage,
        copper_grade_percentage=copper_grade_percentage,
        payable_copper_percentage=payable_copper_percentage,
        lme_copper_price_usd_per_tonne=lme_copper_price_usd_per_tonne,
        tc_usd_per_dmt=tc_usd_per_dmt,
        rc_cents_per_lb=rc_cents_per_lb,
        freight_usd_per_dmt=freight_usd_per_dmt,
        impurity_penalty_usd_per_dmt=impurity_penalty_usd_per_dmt,
        byproduct_credit_usd_per_dmt=byproduct_credit_usd_per_dmt,
        fx_rate_usd_to_chf=fx_rate_usd_to_chf,
    )


def show_kpis(result) -> None:
    first_row = st.columns(3)
    second_row = st.columns(3)
    first_row[0].metric("Dry metric tonnes", tonnes(result.dry_metric_tonnes))
    first_row[1].metric("Payable copper tonnes", tonnes(result.payable_copper_tonnes))
    first_row[2].metric(
        "Gross payable copper value", money(result.gross_copper_value_usd)
    )
    second_row[0].metric("Total deductions", money(result.total_deductions_usd))
    second_row[1].metric("Net shipment value", money(result.net_value_usd))
    second_row[2].metric("Value per dmt", f"${result.value_per_dmt_usd:,.2f}/dmt")


def show_bridge_chart(result) -> None:
    bridge = valuation_bridge(result)
    chart_data = pd.DataFrame(
        {"Component": list(bridge.keys()), "Value USD": list(bridge.values())}
    )
    colors = [
        "#2E7D5B" if value >= 0 else "#B44A3F" for value in chart_data["Value USD"]
    ]
    fig = go.Figure(
        go.Bar(
            x=chart_data["Component"],
            y=chart_data["Value USD"],
            marker_color=colors,
            text=[money(value) for value in chart_data["Value USD"]],
            textposition="outside",
        )
    )
    fig.update_layout(
        title="Shipment Value Bridge",
        yaxis_title="USD",
        xaxis_title="",
        showlegend=False,
        margin=dict(l=20, r=20, t=60, b=80),
    )
    st.plotly_chart(fig, use_container_width=True)


def show_sensitivity_heatmap(assumptions: ConcentrateAssumptions) -> None:
    heatmap = sensitivity_heatmap(assumptions)
    pivot = heatmap.pivot(
        index="TC USD/dmt", columns="Copper price USD/t", values="Net value USD"
    )
    fig = px.imshow(
        pivot,
        labels=dict(x="Copper price USD/t", y="TC USD/dmt", color="Net value USD"),
        color_continuous_scale="RdYlGn",
        aspect="auto",
    )
    fig.update_layout(title="Net Value Sensitivity: Copper Price vs TC")
    st.plotly_chart(fig, use_container_width=True)


def show_scenarios(assumptions: ConcentrateAssumptions) -> pd.DataFrame:
    scenarios = build_scenarios(assumptions)
    tick_labels = {
        "Base case": "Base<br>case",
        "Lower copper price": "Lower<br>copper<br>price",
        "Higher copper price": "Higher<br>copper<br>price",
        "Lower TC/RC market": "Lower<br>TC/RC<br>market",
        "Higher freight/logistics cost": "Higher<br>freight/logistics<br>cost",
        "High impurity penalty case": "High impurity<br>penalty<br>case",
    }
    x_positions = list(range(len(scenarios)))
    colors = px.colors.qualitative.Safe[: len(scenarios)]

    fig = go.Figure(
        go.Bar(
            x=x_positions,
            y=scenarios["Net shipment value USD"],
            marker_color=colors,
            text=[money(value) for value in scenarios["Net shipment value USD"]],
            textposition="outside",
            textfont_size=15,
            marker_line_width=0,
            width=0.74,
            customdata=scenarios["Scenario"],
            hovertemplate="<b>%{customdata}</b><br>Net value: $%{y:,.0f}<extra></extra>",
        )
    )
    y_max = scenarios["Net shipment value USD"].max() * 1.16
    fig.update_layout(
        title="Scenario Comparison",
        height=580,
        showlegend=False,
        xaxis_title="",
        yaxis_title="Net shipment value (USD)",
        margin=dict(l=35, r=35, t=80, b=120),
        uniformtext_minsize=13,
        uniformtext_mode="show",
    )
    fig.update_xaxes(
        tickmode="array",
        tickvals=x_positions,
        ticktext=[tick_labels[name] for name in scenarios["Scenario"]],
        tickfont=dict(size=12),
        tickangle=0,
        automargin=True,
        range=[-0.55, len(scenarios) - 0.45],
    )
    fig.update_yaxes(tickformat=",.0f", range=[0, y_max])
    st.plotly_chart(fig, use_container_width=True)
    return scenarios


def show_risk_section(assumptions: ConcentrateAssumptions) -> None:
    st.subheader("Risk and Commercial Sensitivities")
    price_impact = copper_price_move_impact(assumptions)
    charge_impact = charge_move_impact(assumptions)
    driver, impact = largest_selected_risk_driver(assumptions)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**5% copper price move**")
        price_impact_display = price_impact.copy()
        price_impact_display["LME copper price USD/t"] = price_impact_display[
            "LME copper price USD/t"
        ].map("{:,.0f}".format)
        price_impact_display["Gross copper value USD"] = price_impact_display[
            "Gross copper value USD"
        ].map("{:,.0f}".format)
        price_impact_display["Net shipment value USD"] = price_impact_display[
            "Net shipment value USD"
        ].map("{:,.0f}".format)
        render_html_table(price_impact_display)
    with col2:
        st.markdown("**TC and RC moves**")
        charge_impact_display = charge_impact.copy()
        charge_impact_display["Net shipment value USD"] = charge_impact_display[
            "Net shipment value USD"
        ].map("{:,.0f}".format)
        charge_impact_display["Impact vs base USD"] = charge_impact_display[
            "Impact vs base USD"
        ].map("{:,.0f}".format)
        render_html_table(charge_impact_display)

    st.info(
        f"Largest selected impact: {driver}, changing net value by {money(impact)}. "
        "A commercial, operations, risk, or analyst team could use this type of "
        "tool to compare shipment quality, understand margin drivers, test "
        "commercial terms, and brief traders before negotiating TC/RC, freight, "
        "or impurity clauses."
    )


def main() -> None:
    assumptions = build_assumptions_from_sidebar()
    result = calculate_valuation(assumptions)

    st.title("Copper Concentrate Trade Economics Dashboard")
    st.write(
        "A simplified educational tool for understanding copper concentrate "
        "shipment economics. It focuses on physical trade value drivers such as "
        "quality, payable metal, treatment and refining charges, logistics, "
        "impurity penalties, and by-product credits."
    )

    if result.dry_metric_tonnes <= 0:
        st.error("Dry metric tonnes are zero. Increase shipment size or reduce moisture.")
        return

    show_kpis(result)

    st.warning(
        "TC is charged per dry metric tonne of concentrate because it relates to "
        "treating the bulk material. RC is charged per pound of payable copper "
        "because it relates to refining the contained payable metal."
    )

    st.caption(
        f"Unit conversion used: 1 metric tonne = 2,204.62262 lb. "
        f"Indicative net value in CHF at selected FX: CHF {result.net_value_chf:,.0f}."
    )

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Value Bridge", "Sensitivity", "Scenarios", "Risk View"]
    )
    with tab1:
        show_bridge_chart(result)
        detail = pd.DataFrame(
            [
                {"Metric": "Contained copper tonnes", "Value": result.contained_copper_tonnes},
                {"Metric": "Payable copper pounds", "Value": result.payable_copper_lb},
                {"Metric": "Treatment charge USD", "Value": result.treatment_charge_usd},
                {"Metric": "Refining charge USD", "Value": result.refining_charge_usd},
                {"Metric": "Freight cost USD", "Value": result.freight_cost_usd},
                {"Metric": "Impurity penalty USD", "Value": result.impurity_penalty_usd},
                {"Metric": "By-product credit USD", "Value": result.byproduct_credit_usd},
            ]
        )
        detail_display = detail.copy()
        detail_display["Value"] = detail_display["Value"].map("{:,.2f}".format)
        render_html_table(detail_display)
    with tab2:
        show_sensitivity_heatmap(assumptions)
    with tab3:
        scenario_table = show_scenarios(assumptions)
        scenario_display = scenario_table.copy()
        scenario_display["Copper price USD/t"] = scenario_display[
            "Copper price USD/t"
        ].map("{:,.0f}".format)
        scenario_display["TC USD/dmt"] = scenario_display["TC USD/dmt"].map(
            "{:,.2f}".format
        )
        scenario_display["RC US¢/lb"] = scenario_display["RC US¢/lb"].map(
            "{:,.2f}".format
        )
        scenario_display["Freight USD/dmt"] = scenario_display[
            "Freight USD/dmt"
        ].map("{:,.2f}".format)
        scenario_display["Impurity penalty USD/dmt"] = scenario_display[
            "Impurity penalty USD/dmt"
        ].map("{:,.2f}".format)
        scenario_display["Net shipment value USD"] = scenario_display[
            "Net shipment value USD"
        ].map("{:,.0f}".format)
        scenario_display["Value per dmt USD"] = scenario_display[
            "Value per dmt USD"
        ].map("{:,.2f}".format)
        render_html_table(scenario_display)
    with tab4:
        show_risk_section(assumptions)



if __name__ == "__main__":
    main()
