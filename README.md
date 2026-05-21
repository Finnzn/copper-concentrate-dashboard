# Copper Concentrate Trade Economics Dashboard

A Python and Streamlit project modeling the simplified economics of a copper concentrate shipment. The project was built out of curiosity about physical non-ferrous commodity trading, especially the way cargo quality, processing terms, logistics, and market prices interact in real commercial decisions.

## Why This Project Exists

Copper concentrate is a useful case study because it sits between mining, logistics, smelting, finance, and market risk. Unlike exchange-traded copper cathode, concentrate is not a uniform product. Each shipment can differ by mine source, mineralogy, moisture, copper grade, impurities, precious metal credits, logistics route, and suitability for specific smelters.

This dashboard explores the physical trade economics behind a cargo. The goal is to make the valuation bridge transparent: start with payable copper value, then deduct treatment charges, refining charges, freight, impurity penalties, and add any by-product credits.

## What the Dashboard Models

The model starts with wet metric tonnes and moisture to calculate dry metric tonnes. It then estimates contained copper, payable copper, gross payable copper value, treatment charges, refining charges, freight, impurity penalties, by-product credits, and net shipment value.

Core outputs include:

- Dry metric tonnes
- Payable copper tonnes
- Gross payable copper value
- Total deductions
- Net shipment value
- Value per dry metric tonne
- Sensitivity to copper price and treatment charges
- Scenario comparisons across market and quality cases
- Simple risk impact from copper price, TC, and RC moves

## Why Copper Concentrate Valuation Is Specialized

Copper concentrate valuation is not simply:

```text
copper price * shipment size
```

The buyer is not purchasing pure copper cathode. The buyer is purchasing a physical concentrate with moisture, grade, mineralogy, impurities, logistics constraints, and smelter processing economics. A lower copper price can reduce value, but a higher treatment charge, higher freight cost, or impurity penalty can also materially change the commercial result.

This is why a cargo with a higher copper grade is not automatically the best cargo. Payable metal terms, impurities, freight route, by-product credits, and smelter suitability can all change the economics.

## Why TC Is USD/dmt and RC Is US¢/lb

Treatment charges, or TC, are expressed in USD per dry metric tonne of concentrate, written as USD/dmt, because the charge relates to treating the bulk dry concentrate material.

Refining charges, or RC, are expressed in US cents per pound of payable copper, written as US¢/lb, because the charge relates to refining the contained payable copper metal.

The model uses:

```text
1 metric tonne = 2,204.62262 lb
```

This conversion is required because payable copper is calculated in tonnes while RC is charged in cents per pound.

## Project Structure

```text
copper-concentrate-dashboard/
├── README.md
├── app.py
├── requirements.txt
├── data/
│   ├── sample_lme_prices.csv
│   └── sample_concentrate_specs.csv
├── src/
│   ├── valuation.py
│   ├── risk.py
│   └── scenarios.py
├── notebooks/
│   └── copper_concentrate_market_overview.ipynb
└── docs/
    └── methodology.md
```

## Installation

From the project directory:

```bash
pip install -r requirements.txt
```

Run the Streamlit app:

```bash
streamlit run app.py
```

If the `streamlit` command is not on PATH, this usually also works:

```bash
python3 -m streamlit run app.py
```

## Key Assumptions

- USD is the main project currency.
- FX is optional and shown only as an indicative USD to CHF conversion.
- Copper price is entered manually as USD per metric tonne.
- TC is modeled as USD/dmt.
- RC is modeled as US¢/lb of payable copper.
- Freight, impurity penalties, and by-product credits are simplified as USD/dmt.
- Payable copper is entered as a single percentage of contained copper.
- The model uses illustrative sample data and user-entered assumptions.

## Limitations

This is an educational model, not a tool for live trading decisions. It does not include detailed assay exchange, quotational periods, provisional pricing, hedging execution, financing costs, counterparty credit, insurance, taxes, final settlement, demurrage, smelter-specific penalty schedules, or detailed payable formulas for precious metals.

## Possible Extensions: Benefits and Challenges

### Live LME Copper Prices

Benefit: Live or regularly updated price data would make the dashboard more realistic and would allow users to test shipment value against current market conditions.

Challenge: Reliable market data often requires licensed data access. The app would also need timestamp handling, fallback data, and clear separation between delayed, indicative, and live prices.

### FX Data Integration

Benefit: FX integration would help analyze exposures when costs, financing, or reporting are not all in USD.

Challenge: FX rates depend on timing, source, and settlement convention. A serious model would need to distinguish spot rates, forward rates, and accounting/reporting rates.

### Freight Indices and Route-Specific Logistics

Benefit: Route-based freight assumptions would make the logistics deduction more realistic and help compare origin-destination economics.

Challenge: Freight is not just one number. A better model may need ocean freight, inland transport, port costs, insurance, storage, demurrage, laytime, vessel size, and cargo readiness timing.

### Smelter-Specific Constraints

Benefit: Smelter-specific rules would show why the same concentrate can have different value depending on the buyer. This would make the quality and impurity logic much more realistic.

Challenge: Smelter terms are detailed and often confidential. Modeling them properly requires element-by-element thresholds, penalty schedules, blending constraints, and treatment capacity assumptions.

### Quotational Period and Provisional Pricing Logic

Benefit: Quotational period logic would connect the model more closely to how physical metals contracts are priced and settled over time.

Challenge: The model would need pricing calendars, shipment timing, provisional invoice logic, final settlement rules, and sensitivity to price movements between shipment and final pricing.

### Hedging Logic and Basis Risk

Benefit: Adding hedge positions would show how a physical cargo's price exposure can be managed and how gross value differs from hedged margin.

Challenge: A realistic hedge module would need hedge ratios, contract dates, futures prices, roll assumptions, cash-flow timing, margin calls, and basis risk between the physical cargo and exchange contract.

### Assay Uncertainty and Moisture Adjustment

Benefit: Assay and moisture simulations would show how uncertainty in quality measurements affects settlement value.

Challenge: This requires assumptions about sampling error, umpire assay procedures, moisture loss, contractual tolerances, and probability distributions for each quality variable.

### ESG and Due-Diligence Checks

Benefit: ESG screening could connect cargo economics with source, traceability, responsible sourcing, and regulatory risk.

Challenge: ESG data can be qualitative, incomplete, and difficult to standardize. A useful model would need clear scoring logic and careful treatment of data quality.

### Counterparty Risk Analysis

Benefit: Counterparty scoring would help connect cargo value with payment risk, delivery risk, and credit exposure.

Challenge: Counterparty risk is multi-dimensional. A meaningful model would need payment terms, credit limits, collateral, jurisdiction, historical performance, and concentration exposure.

### Financing Cost and Working Capital Modeling

Benefit: Financing logic would show how timing affects trade profitability, especially when cash is tied up between purchase, shipment, provisional invoicing, and final settlement.

Challenge: The model would need payment dates, interest rates, discount curves, inventory holding periods, credit terms, and cash-flow timing assumptions.

### Multi-Cargo Portfolio Comparison

Benefit: A portfolio view would allow comparison across multiple cargoes, routes, quality profiles, and market scenarios.

Challenge: The app would need better data structures, portfolio aggregation, filtering, scenario management, and more careful treatment of shared assumptions such as prices, FX, and freight.

## Disclaimer

The dashboard is simplified and uses illustrative assumptions. It is designed to explore physical non-ferrous commodity trading economics and should not be used for commercial decisions.
