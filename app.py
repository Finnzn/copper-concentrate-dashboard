from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.risk import (
    charge_move_impact,
    copper_price_move_impact,
    largest_selected_risk_driver,
    sensitivity_variable_names,
    tornado_impacts,
    two_way_sensitivity_heatmap,
)
from src.scenarios import build_scenarios
from src.valuation import ConcentrateAssumptions, calculate_valuation, valuation_bridge
from copper_monte_carlo.app_integration import render_monte_carlo_page


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

DEFAULT_INPUTS = {
    "wet_metric_tonnes": 10_000.0,
    "moisture_percentage": 8.0,
    "copper_grade_percentage": 26.0,
    "payable_copper_percentage": 96.5,
    "copper_payable_deduction_unit_percentage": 1.0,
    "lme_copper_price_usd_per_tonne": 12_000.0,
    "tc_usd_per_dmt": -40.0,
    "rc_cents_per_lb": -4.0,
    "freight_usd_per_dmt": 49.0,
    "impurity_penalty_usd_per_dmt": 12.0,
    "gold_grade_g_per_dmt": 1.0,
    "gold_payable_percentage": 95.0,
    "gold_price_usd_per_oz": 3_300.0,
    "gold_refining_charge_usd_per_oz": 8.0,
    "silver_grade_g_per_dmt": 80.0,
    "silver_payable_percentage": 90.0,
    "silver_price_usd_per_oz": 40.0,
    "silver_refining_charge_usd_per_oz": 0.45,
    "other_byproduct_credit_usd_per_dmt": 0.0,
    "arsenic_ppm": 1_200.0,
    "bismuth_ppm": 150.0,
    "fluorine_ppm": 500.0,
    "financing_days": 45.0,
    "annual_financing_rate_percentage": 6.0,
    "fx_rate_usd_to_chf": 0.90,
}


st.set_page_config(
    page_title="Copper Concentrate Trade Economics Dashboard",
    page_icon="Cu",
    layout="wide",
)


def money(value: float) -> str:
    return f"${value:,.0f}"


def usd_text(value: float) -> str:
    return f"USD {value:,.0f}"


def tonnes(value: float) -> str:
    return f"{value:,.2f} t"


def apply_dashboard_style() -> None:
    st.markdown(
        """
        <style>
        :root {
            --copper-ink: #18212b;
            --copper-muted: #5b6775;
            --copper-line: rgba(24, 33, 43, 0.14);
            --copper-panel: #f7f9fb;
            --copper-accent: #9f5b35;
            --copper-green: #28785f;
            --copper-red: #a8433e;
        }
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 2.5rem;
        }
        h1, h2, h3 {
            letter-spacing: 0;
        }
        div[data-testid="stMetric"] {
            background: var(--copper-panel);
            border: 1px solid var(--copper-line);
            border-radius: 8px;
            padding: 0.75rem 0.85rem;
        }
        div[data-testid="stMetricLabel"] p {
            color: var(--copper-muted);
            font-size: 0.86rem;
        }
        div[data-testid="stMetricValue"] {
            color: var(--copper-ink);
            font-size: 1.55rem;
        }
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: var(--copper-ink);
        }
        .dashboard-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9rem;
        }
        .dashboard-table th {
            background-color: var(--copper-ink);
            color: #ffffff;
            text-align: left;
            padding: 0.55rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.16);
        }
        .dashboard-table td {
            padding: 0.52rem 0.55rem;
            border-bottom: 1px solid var(--copper-line);
            vertical-align: top;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def section_note(text: str) -> None:
    st.caption(text)


def render_html_table(df: pd.DataFrame) -> None:
    """Render a small table without Streamlit's pyarrow-backed dataframe path."""

    st.markdown(
        df.to_html(index=False, escape=True, classes="dashboard-table"),
        unsafe_allow_html=True,
    )


def format_display_table(
    df: pd.DataFrame, formats: dict[str, str], columns: list[str] | None = None
) -> pd.DataFrame:
    display = df.copy()
    if columns is not None:
        display = display[columns]
    for column, number_format in formats.items():
        display[column] = display[column].map(number_format.format)
    return display


@st.cache_data
def load_sample_concentrates() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "sample_concentrate_specs.csv")


@st.cache_data
def load_sample_lme_prices() -> pd.DataFrame:
    prices = pd.read_csv(DATA_DIR / "sample_lme_prices.csv", parse_dates=["date"])
    defaults = {
        "tc_usd_per_dmt": DEFAULT_INPUTS["tc_usd_per_dmt"],
        "rc_cents_per_lb": DEFAULT_INPUTS["rc_cents_per_lb"],
        "freight_usd_per_dmt": DEFAULT_INPUTS["freight_usd_per_dmt"],
        "gold_price_usd_per_oz": DEFAULT_INPUTS["gold_price_usd_per_oz"],
        "silver_price_usd_per_oz": DEFAULT_INPUTS["silver_price_usd_per_oz"],
        "fx_rate_usd_to_chf": DEFAULT_INPUTS["fx_rate_usd_to_chf"],
        "annual_financing_rate_percentage": DEFAULT_INPUTS[
            "annual_financing_rate_percentage"
        ],
        "source_note": "Illustrative market assumptions",
    }
    for column, default in defaults.items():
        if column not in prices.columns:
            prices[column] = default
    return prices.sort_values("date")


def initialize_sidebar_state() -> None:
    for key, value in DEFAULT_INPUTS.items():
        st.session_state.setdefault(key, value)
    st.session_state.setdefault("active_sample_concentrate", "Manual inputs")


def apply_sample_to_sidebar(sample: pd.Series) -> None:
    sample_fields = [
        "wet_metric_tonnes",
        "moisture_percentage",
        "copper_grade_percentage",
        "payable_copper_percentage",
        "tc_usd_per_dmt",
        "rc_cents_per_lb",
        "freight_usd_per_dmt",
        "impurity_penalty_usd_per_dmt",
    ]
    for field in sample_fields:
        st.session_state[field] = float(sample[field])

    st.session_state["other_byproduct_credit_usd_per_dmt"] = float(
        sample.get("byproduct_credit_usd_per_dmt", 0.0)
    )


def build_assumptions_from_sidebar() -> ConcentrateAssumptions:
    initialize_sidebar_state()
    sample_concentrates = load_sample_concentrates()
    sample_names = ["Manual inputs"] + sample_concentrates["concentrate_name"].tolist()

    st.sidebar.header("Cargo Case")
    selected_sample = st.sidebar.selectbox(
        "Starting point",
        sample_names,
        index=sample_names.index(st.session_state.active_sample_concentrate),
        help="Choose a sample cargo or keep manual inputs.",
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
        st.sidebar.caption("Manual case: edit quality, prices, charges, and financing below.")

    with st.sidebar.expander("1. Cargo Quality", expanded=True):
        wet_metric_tonnes = st.number_input(
            "Shipment size, wet metric tonnes (wmt)",
            min_value=0.0,
            step=100.0,
            key="wet_metric_tonnes",
        )
        moisture_percentage = st.slider(
            "Moisture percentage (%)",
            min_value=0.0,
            max_value=20.0,
            step=0.1,
            key="moisture_percentage",
        )
        copper_grade_percentage = st.slider(
            "Copper grade (%)",
            min_value=0.0,
            max_value=60.0,
            step=0.1,
            key="copper_grade_percentage",
        )
        payable_copper_percentage = st.slider(
            "Payable copper (%)",
            min_value=0.0,
            max_value=100.0,
            step=0.1,
            key="payable_copper_percentage",
        )
        copper_payable_deduction_unit_percentage = st.number_input(
            "Payable deduction unit (% Cu)",
            min_value=0.0,
            max_value=10.0,
            step=0.1,
            key="copper_payable_deduction_unit_percentage",
            help="Alternative payability rule: payable copper is limited by grade less this deduction.",
        )

    with st.sidebar.expander("2. Market Terms and Charges", expanded=True):
        lme_copper_price_usd_per_tonne = st.number_input(
            "LME copper price (USD per metric tonne)",
            min_value=0.0,
            step=50.0,
            key="lme_copper_price_usd_per_tonne",
        )
        tc_usd_per_dmt = st.number_input(
            "Treatment charge, TC (USD/dmt)",
            min_value=-200.0,
            step=1.0,
            key="tc_usd_per_dmt",
            help="Positive TC reduces value; negative TC acts as a commercial credit.",
        )
        rc_cents_per_lb = st.number_input(
            "Refining charge, RC (US cents/lb)",
            min_value=-20.0,
            step=0.25,
            key="rc_cents_per_lb",
            help="Applied to payable copper pounds.",
        )
        freight_usd_per_dmt = st.number_input(
            "Freight/logistics cost (USD/dmt)",
            min_value=0.0,
            step=1.0,
            key="freight_usd_per_dmt",
        )

    with st.sidebar.expander("3. Precious-Metal Credits"):
        gold_grade_g_per_dmt = st.number_input(
            "Gold grade (g/dmt)",
            min_value=0.0,
            step=0.1,
            key="gold_grade_g_per_dmt",
        )
        gold_payable_percentage = st.slider(
            "Gold payable (%)",
            min_value=0.0,
            max_value=100.0,
            step=1.0,
            key="gold_payable_percentage",
        )
        gold_price_usd_per_oz = st.number_input(
            "Gold price (USD/oz)",
            min_value=0.0,
            step=25.0,
            key="gold_price_usd_per_oz",
        )
        gold_refining_charge_usd_per_oz = st.number_input(
            "Gold refining charge (USD/oz)",
            min_value=0.0,
            step=0.5,
            key="gold_refining_charge_usd_per_oz",
        )
        silver_grade_g_per_dmt = st.number_input(
            "Silver grade (g/dmt)",
            min_value=0.0,
            step=1.0,
            key="silver_grade_g_per_dmt",
        )
        silver_payable_percentage = st.slider(
            "Silver payable (%)",
            min_value=0.0,
            max_value=100.0,
            step=1.0,
            key="silver_payable_percentage",
        )
        silver_price_usd_per_oz = st.number_input(
            "Silver price (USD/oz)",
            min_value=0.0,
            step=0.5,
            key="silver_price_usd_per_oz",
        )
        silver_refining_charge_usd_per_oz = st.number_input(
            "Silver refining charge (USD/oz)",
            min_value=0.0,
            step=0.05,
            key="silver_refining_charge_usd_per_oz",
        )
        other_byproduct_credit_usd_per_dmt = st.number_input(
            "Other by-product credit (USD/dmt)",
            min_value=0.0,
            step=1.0,
            key="other_byproduct_credit_usd_per_dmt",
        )

    with st.sidebar.expander("4. Impurities, Finance and FX"):
        impurity_penalty_usd_per_dmt = st.number_input(
            "Flat impurity penalty (USD/dmt)",
            min_value=0.0,
            step=1.0,
            key="impurity_penalty_usd_per_dmt",
        )
        arsenic_ppm = st.number_input(
            "Arsenic assay (ppm)",
            min_value=0.0,
            step=100.0,
            key="arsenic_ppm",
        )
        bismuth_ppm = st.number_input(
            "Bismuth assay (ppm)",
            min_value=0.0,
            step=25.0,
            key="bismuth_ppm",
        )
        fluorine_ppm = st.number_input(
            "Fluorine assay (ppm)",
            min_value=0.0,
            step=50.0,
            key="fluorine_ppm",
        )
        financing_days = st.number_input(
            "Financing days",
            min_value=0.0,
            step=5.0,
            key="financing_days",
        )
        annual_financing_rate_percentage = st.number_input(
            "Annual financing rate (%)",
            min_value=0.0,
            step=0.25,
            key="annual_financing_rate_percentage",
        )
        fx_rate_usd_to_chf = st.number_input(
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
        copper_payable_deduction_unit_percentage=copper_payable_deduction_unit_percentage,
        gold_grade_g_per_dmt=gold_grade_g_per_dmt,
        gold_payable_percentage=gold_payable_percentage,
        gold_price_usd_per_oz=gold_price_usd_per_oz,
        gold_refining_charge_usd_per_oz=gold_refining_charge_usd_per_oz,
        silver_grade_g_per_dmt=silver_grade_g_per_dmt,
        silver_payable_percentage=silver_payable_percentage,
        silver_price_usd_per_oz=silver_price_usd_per_oz,
        silver_refining_charge_usd_per_oz=silver_refining_charge_usd_per_oz,
        other_byproduct_credit_usd_per_dmt=other_byproduct_credit_usd_per_dmt,
        arsenic_ppm=arsenic_ppm,
        bismuth_ppm=bismuth_ppm,
        fluorine_ppm=fluorine_ppm,
        financing_days=financing_days,
        annual_financing_rate_percentage=annual_financing_rate_percentage,
        fx_rate_usd_to_chf=fx_rate_usd_to_chf,
    )


def show_kpis(result, driver: str, impact: float) -> None:
    first_row = st.columns(4)
    second_row = st.columns(4)
    first_row[0].metric("Dry tonnes", tonnes(result.dry_metric_tonnes))
    first_row[1].metric("Payable copper", tonnes(result.payable_copper_tonnes))
    first_row[2].metric("Net shipment value", money(result.net_value_usd))
    first_row[3].metric("Value per dmt", f"${result.value_per_dmt_usd:,.2f}/dmt")
    second_row[0].metric("Gross copper value", money(result.gross_copper_value_usd))
    second_row[1].metric("By-product credits", money(result.byproduct_credit_usd))
    second_row[2].metric("Total deductions", money(result.total_deductions_usd))
    second_row[3].metric(f"Largest quick shock: {driver}", money(impact))


def show_bridge_chart(result) -> None:
    bridge = valuation_bridge(result)
    components = list(bridge.keys()) + ["Net value"]
    values = list(bridge.values()) + [result.net_value_usd]
    measures = ["relative"] * len(bridge) + ["total"]
    text = [money(value) for value in values]

    fig = go.Figure(
        go.Waterfall(
            x=components,
            y=values,
            measure=measures,
            text=text,
            textposition="outside",
            connector={"line": {"color": "rgba(80, 80, 80, 0.45)"}},
            increasing={"marker": {"color": "#28785F"}},
            decreasing={"marker": {"color": "#A8433E"}},
            totals={"marker": {"color": "#18212B"}},
        )
    )
    fig.update_layout(
        title="How Gross Copper Value Becomes Net Shipment Value",
        yaxis_title="Value impact (USD)",
        xaxis_title="",
        showlegend=False,
        height=560,
        margin=dict(l=20, r=20, t=60, b=90),
    )
    st.plotly_chart(fig, use_container_width=True)
    section_note(
        "Waterfall bars show each addition or deduction from payable copper value. "
        "A negative TC/RC appears as a credit because it increases net value."
    )


def show_sensitivity_heatmap(assumptions: ConcentrateAssumptions) -> None:
    variables = sensitivity_variable_names()
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        x_variable = st.selectbox(
            "Horizontal driver",
            variables,
            index=variables.index("Copper price"),
        )
    with col2:
        y_options = [variable for variable in variables if variable != x_variable]
        default_y = "TC" if "TC" in y_options else y_options[0]
        y_variable = st.selectbox(
            "Vertical driver",
            y_options,
            index=y_options.index(default_y),
        )
    with col3:
        steps = st.slider(
            "Grid detail",
            min_value=5,
            max_value=13,
            value=9,
            step=2,
        )

    heatmap = two_way_sensitivity_heatmap(
        assumptions,
        x_variable=x_variable,
        y_variable=y_variable,
        steps=steps,
    )
    x_label = heatmap.columns[0]
    y_label = heatmap.columns[1]
    pivot = heatmap.pivot(
        index=y_label, columns=x_label, values="Net value USD"
    )
    fig = px.imshow(
        pivot,
        labels=dict(x=x_label, y=y_label, color="Net value (USD)"),
        color_continuous_scale="RdYlGn",
        aspect="auto",
    )
    fig.update_layout(
        title=f"Net Shipment Value Across {x_variable} and {y_variable}",
        margin=dict(l=35, r=35, t=70, b=55),
    )
    st.plotly_chart(fig, use_container_width=True)
    section_note(
        "Each cell recalculates the same cargo using the two selected drivers. "
        "Green cells have higher net shipment value; red cells have lower value."
    )

    sensitivity_display = format_display_table(
        heatmap,
        {
            x_label: "{:,.2f}",
            y_label: "{:,.2f}",
            "Net value USD": "{:,.0f}",
        },
    )
    render_html_table(sensitivity_display)


def show_market_data(assumptions: ConcentrateAssumptions) -> None:
    market = load_sample_lme_prices()

    def value_with_market_row(row: pd.Series) -> float:
        market_assumptions = ConcentrateAssumptions(
            **{
                **assumptions.__dict__,
                "lme_copper_price_usd_per_tonne": float(
                    row["copper_price_usd_per_tonne"]
                ),
                "tc_usd_per_dmt": float(row["tc_usd_per_dmt"]),
                "rc_cents_per_lb": float(row["rc_cents_per_lb"]),
                "freight_usd_per_dmt": float(row["freight_usd_per_dmt"]),
                "gold_price_usd_per_oz": float(row["gold_price_usd_per_oz"]),
                "silver_price_usd_per_oz": float(row["silver_price_usd_per_oz"]),
                "fx_rate_usd_to_chf": float(row["fx_rate_usd_to_chf"]),
                "annual_financing_rate_percentage": float(
                    row["annual_financing_rate_percentage"]
                ),
            }
        )
        return calculate_valuation(market_assumptions).net_value_usd

    market["Shipment value USD"] = market.apply(value_with_market_row, axis=1)

    section_note(
        "This view keeps the selected cargo quality constant and changes only "
        "illustrative market terms across dates."
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=market["date"],
            y=market["copper_price_usd_per_tonne"],
            mode="lines+markers",
            name="Copper price (USD/t)",
            yaxis="y",
            line=dict(color="#9F5B35", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=market["date"],
            y=market["Shipment value USD"],
            mode="lines+markers",
            name="Net shipment value (USD)",
            yaxis="y2",
            line=dict(color="#28785F", width=3),
        )
    )
    fig.update_layout(
        title="Same Cargo Revalued Under Illustrative Market Terms",
        yaxis=dict(title="Copper price USD/t"),
        yaxis2=dict(title="Net shipment value USD", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=35, r=35, t=70, b=50),
    )
    st.plotly_chart(fig, use_container_width=True)

    price_display = market.rename(
        columns={
            "date": "Date",
            "copper_price_usd_per_tonne": "Copper price USD/t",
            "tc_usd_per_dmt": "TC USD/dmt",
            "rc_cents_per_lb": "RC US cents/lb",
            "freight_usd_per_dmt": "Freight USD/dmt",
            "gold_price_usd_per_oz": "Gold price USD/oz",
            "silver_price_usd_per_oz": "Silver price USD/oz",
            "fx_rate_usd_to_chf": "USD/CHF",
            "annual_financing_rate_percentage": "Financing rate %",
        }
    )
    price_display["Date"] = price_display["Date"].dt.date.astype(str)
    price_display = format_display_table(
        price_display,
        {
            "Copper price USD/t": "{:,.0f}",
            "TC USD/dmt": "{:,.2f}",
            "RC US cents/lb": "{:,.2f}",
            "Freight USD/dmt": "{:,.2f}",
            "Gold price USD/oz": "{:,.0f}",
            "Silver price USD/oz": "{:,.2f}",
            "USD/CHF": "{:.4f}",
            "Financing rate %": "{:.2f}",
            "Shipment value USD": "{:,.0f}",
        },
        [
            "Date",
            "Copper price USD/t",
            "TC USD/dmt",
            "RC US cents/lb",
            "Freight USD/dmt",
            "Gold price USD/oz",
            "Silver price USD/oz",
            "USD/CHF",
            "Financing rate %",
            "Shipment value USD",
        ],
    )
    render_html_table(price_display)


def show_scenarios(assumptions: ConcentrateAssumptions) -> pd.DataFrame:
    scenarios = build_scenarios(assumptions)
    fig = px.bar(
        scenarios,
        x="Scenario",
        y="Net shipment value USD",
        color="Scenario",
        text=scenarios["Net shipment value USD"].map(lambda value: money(value)),
        color_discrete_sequence=["#28785F", "#9F5B35", "#5B6775", "#A8433E", "#426E86"],
    )
    y_max = max(0.0, float(scenarios["Net shipment value USD"].max()))
    y_min = min(0.0, float(scenarios["Net shipment value USD"].min()))
    y_padding = max(abs(y_max - y_min) * 0.18, 1.0)
    fig.update_traces(
        textposition="outside",
        textfont_size=12,
        cliponaxis=False,
        hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>",
    )
    fig.update_layout(
        title="Scenario Comparison: Net Shipment Value",
        height=620,
        showlegend=False,
        xaxis_title="",
        yaxis_title="Net shipment value (USD)",
        bargap=0.28,
        margin=dict(l=35, r=35, t=115, b=170),
    )
    fig.update_xaxes(tickangle=-30, automargin=True)
    fig.update_yaxes(tickformat=",.0f", range=[y_min - y_padding, y_max + y_padding])
    st.plotly_chart(fig, use_container_width=True)
    section_note(
        "Scenario bars start from the current sidebar case, then apply selected "
        "market, charge, freight, and quality shocks."
    )
    return scenarios


def show_tornado_chart(assumptions: ConcentrateAssumptions) -> pd.DataFrame:
    tornado = tornado_impacts(assumptions)
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=tornado["Driver"],
            x=tornado["Low impact USD"],
            orientation="h",
            name="Low case",
            marker_color="#A8433E",
            hovertemplate="%{y}<br>Impact: $%{x:,.0f}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            y=tornado["Driver"],
            x=tornado["High impact USD"],
            orientation="h",
            name="High case",
            marker_color="#28785F",
            hovertemplate="%{y}<br>Impact: $%{x:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        title="Ranked Value Drivers",
        barmode="overlay",
        xaxis_title="Impact versus base case (USD)",
        yaxis_title="",
        height=520,
        margin=dict(l=35, r=35, t=70, b=40),
    )
    fig.add_vline(x=0, line_width=1, line_color="#18212B")
    st.plotly_chart(fig, use_container_width=True)
    section_note(
        "The longest bars are the shocks with the biggest dollar effect versus "
        "the current base case."
    )
    return tornado


def show_risk_section(assumptions: ConcentrateAssumptions) -> None:
    st.subheader("Quick Risk Briefing")
    section_note(
        "Use this page to identify which commercial terms deserve the most attention "
        "before negotiating, hedging, or stress-testing a shipment."
    )
    price_impact = copper_price_move_impact(assumptions)
    charge_impact = charge_move_impact(assumptions)
    driver, impact = largest_selected_risk_driver(assumptions)

    show_tornado_chart(assumptions)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Copper price shock: +/-5%**")
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
        st.markdown("**Smelter charge shocks**")
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
        "Use this as a quick commercial briefing view before negotiating price, "
        "TC/RC, freight, quality, impurity, or working-capital terms."
    )


def show_detail_table(result) -> None:
    detail = pd.DataFrame(
        [
            {"Metric": "Contained copper tonnes", "Value": result.contained_copper_tonnes},
            {
                "Metric": "Payable copper by percentage tonnes",
                "Value": result.payable_copper_by_percentage_tonnes,
            },
            {
                "Metric": "Payable copper by deduction tonnes",
                "Value": result.payable_copper_by_deduction_tonnes,
            },
            {"Metric": "Payable copper pounds", "Value": result.payable_copper_lb},
            {"Metric": "Treatment charge USD", "Value": result.treatment_charge_usd},
            {"Metric": "Refining charge USD", "Value": result.refining_charge_usd},
            {"Metric": "Freight cost USD", "Value": result.freight_cost_usd},
            {"Metric": "Flat impurity penalty USD", "Value": result.flat_impurity_penalty_usd},
            {"Metric": "Arsenic penalty USD", "Value": result.arsenic_penalty_usd},
            {"Metric": "Bismuth penalty USD", "Value": result.bismuth_penalty_usd},
            {"Metric": "Fluorine penalty USD", "Value": result.fluorine_penalty_usd},
            {"Metric": "Gold payable ounces", "Value": result.gold_payable_oz},
            {"Metric": "Silver payable ounces", "Value": result.silver_payable_oz},
            {"Metric": "Gold credit USD", "Value": result.gold_credit_usd},
            {"Metric": "Silver credit USD", "Value": result.silver_credit_usd},
            {"Metric": "Other by-product credit USD", "Value": result.other_byproduct_credit_usd},
            {"Metric": "Financing cost USD", "Value": result.financing_cost_usd},
        ]
    )
    detail_display = detail.copy()
    detail_display["Value"] = detail_display["Value"].map("{:,.2f}".format)
    st.subheader("Calculation Detail")
    section_note(
        "Trace the physical conversion and commercial line items behind the KPIs."
    )
    render_html_table(detail_display)


def main() -> None:
    apply_dashboard_style()
    page = st.sidebar.radio(
        "Dashboard page",
        ["Concentrate Valuation", "Copper Monte Carlo Risk"],
    )
    if page == "Copper Monte Carlo Risk":
        render_monte_carlo_page()
        return

    assumptions = build_assumptions_from_sidebar()
    result = calculate_valuation(assumptions)
    driver, impact = largest_selected_risk_driver(assumptions)

    st.title("Copper Concentrate Economics")
    st.write(
        "Price one shipment from wet tonnes through payable copper, by-product "
        "credits, smelter charges, freight, impurity penalties, financing, and FX."
    )

    if result.dry_metric_tonnes <= 0:
        st.error("Dry metric tonnes are zero. Increase shipment size or reduce moisture.")
        return

    st.success(
        f"Commercial read: net value is {usd_text(result.net_value_usd)} "
        f"({result.value_per_dmt_usd:,.2f} USD/dmt). "
        f"The largest quick shock is {driver}, with an impact of {money(impact)}."
    )
    show_kpis(result, driver, impact)

    st.info(
        "Workflow: set the cargo case in the sidebar, read the headline economics, "
        "then move through the tabs from value bridge to sensitivities, scenarios, "
        "market revaluation, and risk briefing."
    )

    st.caption(
        "Unit conversion used: 1 metric tonne = 2,204.62262 lb. "
        f"Indicative net value in CHF at selected FX: CHF {result.net_value_chf:,.0f}."
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Value Bridge", "Sensitivity", "Scenarios", "Market Data", "Risk View"]
    )
    with tab1:
        show_bridge_chart(result)
        show_detail_table(result)
    with tab2:
        show_sensitivity_heatmap(assumptions)
    with tab3:
        scenario_table = show_scenarios(assumptions)
        scenario_display = format_display_table(
            scenario_table,
            {
                "Copper price USD/t": "{:,.2f}",
                "TC USD/dmt": "{:,.2f}",
                "RC US¢/lb": "{:,.2f}",
                "Freight USD/dmt": "{:,.2f}",
                "Impurity penalty USD/dmt": "{:,.2f}",
                "Net shipment value USD": "{:,.2f}",
                "Value per dmt USD": "{:,.2f}",
            },
        )
        render_html_table(scenario_display)
    with tab4:
        show_market_data(assumptions)
    with tab5:
        show_risk_section(assumptions)


if __name__ == "__main__":
    main()
