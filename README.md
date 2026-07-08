# Copper Concentrate Trade Economics Dashboard

A Python and Streamlit project modeling the simplified economics of a copper concentrate shipment. The project was built out of curiosity about physical non-ferrous commodity trading, especially the way cargo quality, processing terms, logistics, and market prices interact in real commercial decisions.

## Why This Project Exists

Copper concentrate is a useful case study because it sits between mining, logistics, smelting, finance, and market risk. Unlike exchange-traded copper cathode, concentrate is not a uniform product. Each shipment can differ by mine source, mineralogy, moisture, copper grade, impurities, precious metal credits, logistics route, and suitability for specific smelters.

This dashboard explores the physical trade economics behind a cargo. The goal is to make the valuation bridge transparent: start with payable copper value, then deduct treatment charges, refining charges, freight, impurity penalties, and add any by-product credits.

## What the Dashboard Models

The model starts with wet metric tonnes and moisture to calculate dry metric tonnes. It then estimates contained copper, payable copper using a simplified "lesser of" payable rule, gross payable copper value, treatment charges, refining charges, freight, impurity penalties, precious metal credits, financing cost, and net shipment value.

Core outputs include:

- Dry metric tonnes
- Payable copper tonnes
- Gross payable copper value
- Total deductions
- Net shipment value
- Value per dry metric tonne
- Gold and silver by-product credits
- Element-level impurity penalty estimates
- Financing cost over the settlement period
- Two-way sensitivity analysis across selected value drivers
- Illustrative market-assumptions cargo value view
- Scenario comparisons across market and quality cases
- Tornado-style ranking of selected value drivers

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

## How to Read the Dashboard

The sidebar defines the base cargo and base commercial terms. It controls the shipment size, quality, payable copper terms, copper price, TC/RC, freight, impurities, precious metal assumptions, financing, and FX.

The main tabs use that base case in different ways:

- **Value Bridge** shows the full shipment valuation from gross payable copper value through deductions, credits, financing cost, and final net value.
- **Sensitivity** revalues the same base cargo across two selected drivers. For example, copper price versus TC, copper price versus freight, arsenic versus TC, or moisture versus freight.
- **Scenarios** starts from the base case and applies predefined shocks such as lower copper price, higher freight, or higher impurity penalties.
- **Market Data** keeps the selected cargo quality constant and revalues that same cargo against illustrative market assumptions by date. The sample market table varies copper price, TC/RC, freight, precious metal prices, FX, and financing rate.
- **Risk View** ranks selected value drivers by impact and shows quick copper price, TC, and RC move tables.

## Project Structure

```text
copper-concentrate-dashboard/
├── README.md
├── app.py
├── requirements.txt
├── copper_monte_carlo/
│   ├── config.py
│   ├── data_loader.py
│   ├── stochastic_processes.py
│   ├── simulation_engine.py
│   ├── concentrate_valuation.py
│   ├── risk_metrics.py
│   ├── plots.py
│   ├── app_integration.py
│   └── data/
│       └── default_assumptions.yaml
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

`data/sample_lme_prices.csv` is intentionally broader than a pure price file. It contains illustrative market assumptions by date, including copper price, TC/RC, freight, precious metal prices, FX, and financing rate. These are sample assumptions only, not live or licensed market data.

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
- Freight and flat impurity penalties are simplified as USD/dmt.
- Payable copper is modeled as the lower of percentage payable copper and a deduction-unit formula.
- Gold and silver credits use illustrative grades, payable rates, prices, and refining charges.
- Arsenic, bismuth, and fluorine penalties use simplified threshold schedules.
- Financing cost uses simple interest over selected financing days.
- The model uses illustrative sample data and user-entered assumptions.
- The market data tab values the same selected cargo quality against changing illustrative market terms such as copper price, TC/RC, freight, precious metal prices, FX, and financing rate.
- The sensitivity tab shows full net cargo value, not shipment size multiplied by price. Each heatmap cell reruns the full valuation model.

## Copper Monte Carlo Risk Module

The project now includes a path-based Monte Carlo package in `copper_monte_carlo/`.
It simulates monthly paths for copper price, TC, RC, freight, FX, basis, and physical
trade margin over a configurable 12, 24, or 36 month horizon.

The first working version implements:

- Copper price paths using geometric Brownian motion with optional jump shocks.
- TC and RC paths using mean-reverting processes.
- Freight paths using mean reversion with optional disruption jumps.
- FX paths and basis paths for future hedging/basis extensions.
- Vectorized concentrate economics for gross metal value, payable copper, TC/RC,
  freight, insurance, storage, financing, by-product credits, hedge PnL, unhedged
  margin, and hedged margin.
- Risk metrics including expected margin, P5/P95 margin, probability of loss,
  95% VaR, 95% CVaR, maximum drawdown, and hedge effectiveness.
- Streamlit charts for copper spider plots, fan charts, final price distribution,
  margin fan charts, and final margin distribution.
- Explicit trade modes for concentrate merchant trades, smelter conversion,
  refined copper trading, and the original integrated conversion prototype.

These scenarios are risk simulations, not forecasts. The output should be read as
a distribution of possible outcomes based on assumptions.

### Trade Modes

The Monte Carlo page separates the physical business model from the market
simulation. Available modes are:

- `Concentrate merchant`: buy concentrate from a producer and sell concentrate
  to a smelter. Margin is driven by payable metal value, TC/RC terms, freight,
  storage, financing, and hedge effects.
- `Smelter conversion`: buy concentrate, process it, and sell recovered refined
  copper. This uses recovery-rate and processing-cost assumptions.
- `Refined copper trade`: buy refined copper and sell it onward. TC/RC and
  concentrate quality are not the core economic drivers in this mode.
- `Integrated conversion`: preserves the earlier prototype chain where the user
  buys concentrate exposure, carries it, and sells payable copper equivalent.

### How Trade Modes Are Calculated

All trade modes currently share the same simulated market paths:

- Copper price
- TC
- RC
- Freight
- FX
- Basis

They also share the same logistics and carry assumptions unless the user changes
the sidebar inputs:

- Freight rate
- Storage duration
- Storage cost
- Port cost
- Inland transport cost
- Insurance rate
- Financing rate
- Working-capital days
- Hedge enabled/disabled
- Hedge ratio

This is deliberate for the first version: it lets the user compare business models
under one common market environment. It is also a simplification. A future version
should allow route, shipping duration, warehouse terms, and financing timeline to
vary by trade mode.

#### Concentrate Merchant

This mode approximates:

```text
mine / producer -> trader -> smelter
```

The model calculates an initial concentrate purchase invoice from payable copper
value, purchase percentage, TC, RC, and by-product credit. It then calculates a
simulated sale invoice using the simulated copper price, simulated TC, simulated
RC, and by-product credit.

Simplified formula:

```text
margin =
    simulated concentrate sale invoice
  - initial concentrate purchase invoice
  - freight
  - storage
  - port cost
  - inland transport
  - insurance
  - financing
  + hedge PnL
  - hedge cost
```

TC/RC are part of the concentrate invoice economics. Negative TC/RC are allowed
because the fallback case assumes a very tight concentrate market.

#### Smelter Conversion

This mode approximates:

```text
buy concentrate -> process it -> sell recovered refined copper
```

The model buys concentrate using the same concentrate purchase invoice logic, then
values recovered refined copper using the simulated copper price and a recovery
rate. It deducts a simple processing cost.

Simplified formula:

```text
margin =
    recovered copper tonnes * simulated copper price
  + by-product credit
  - initial concentrate purchase invoice
  - smelting/refining processing cost
  - logistics and carry costs
  + hedge PnL
  - hedge cost
```

This is not yet a full smelter model. It does not yet include energy costs,
capacity utilization, detailed metal recoveries, payable settlement differences,
or smelter-specific impurity schedules.

#### Refined Copper Trade

This mode approximates:

```text
refined copper supplier -> trader -> end user
```

The model ignores TC/RC and concentrate processing economics for the margin
calculation. It assumes the trader buys refined copper at the initial copper price
plus a purchase premium, then sells at the simulated copper price plus a sale
premium.

Simplified formula:

```text
margin =
    refined tonnes * (simulated copper price + sale premium)
  - refined tonnes * (initial copper price + purchase premium)
  - refined freight
  - storage
  - insurance
  - financing
  + hedge PnL
  - hedge cost
```

The current implementation still uses the selected cargo's payable copper tonnes
as the refined tonnes for comparison. A later version should let refined copper
trade size be entered directly in cathode tonnes.

#### Integrated Conversion

This mode preserves the earlier prototype:

```text
buy concentrate exposure -> carry it -> sell payable copper equivalent
```

It is useful as a broad educational stress test, but it is less commercially
precise than the separated modes above.

### Current Trade-Mode Simplifications

The model is intentionally conservative and transparent, but it is still simplified:

- Shipping and carry assumptions are shared across modes unless manually changed.
- Freight is simulated as one generic freight process.
- Concentrate merchant mode does not yet separately model purchase TC/RC and sale
  TC/RC as two independent negotiated books.
- Refined copper mode uses payable copper tonnes as a proxy for refined tonnes.
- Smelter conversion mode has only one recovery rate and one processing-cost input.
- Hedge logic is still simplified and does not yet include futures curve rolls,
  exchange margin calls, or quotational-period pricing.
- Scenario comparison exists as selectable presets, but full side-by-side scenario
  tables are still a later enhancement.

### Interpreting Negative Margins

Negative margins in the current fallback case should not be read as a conclusion
that concentrate trading, smelter conversion, or refined copper trading is
unattractive in general. They mean only that the placeholder deal terms currently
entered into the model do not cover the assumed freight, storage, insurance,
financing, and other carry costs.

The first version is closer to a spot-style trade stress test than a full forward
physical trading book. Real trades may be attractive because of features not yet
fully modeled, such as:

- A forward sale agreed before or shortly after the purchase.
- A futures curve in contango or backwardation.
- A buyer or smelter needing material for a specific future delivery month.
- A stronger future physical premium.
- A TC/RC spread between producer purchase terms and smelter sale terms.
- A quotational-period advantage or mismatch.
- Optionality around storage, timing, blending, destination, or customer demand.
- A hedge that locks in economics rather than simply reacting to simulated spot.

For example, a trader may buy concentrate today, finance and store or ship it, and
sell it for delivery three months later. If the future delivery price, future
physical premium, or forward TC/RC terms are high enough, that forward sale can
compensate for cost of carry. The current model includes carry costs, but it does
not yet include a full forward-curve and delivery-month pricing engine to represent
that trade cleanly.

### Future Expansion: Forward Physical Trading

The most important next expansion is a proper forward-pricing layer. Useful
extensions include:

- Manual futures curve input by delivery month.
- Synthetic futures curves using spot price plus monthly carry.
- Contango/backwardation scenario controls.
- Explicit purchase month, shipment month, arrival month, storage period, and
  sale/delivery month.
- Forward physical sale contracts with delivery-month pricing.
- Separate purchase and sale TC/RC terms for concentrate merchant trades.
- Regional physical premiums by month and destination.
- LME cash, LME 3M, COMEX, and manual reference-price selection.
- Quotational-period pricing, including M, M+1, M+2, and average-month rules.
- Hedge entry and exit month tied to the physical pricing period.
- Hedge roll cost or benefit from the futures curve.
- Storage optionality: sell now, store, or wait for forward premium.
- Inventory-demand scenarios, such as smelters needing concentrate in three months.
- Side-by-side scenario comparison for spot sale, forward sale, stored inventory,
  unhedged, partially hedged, and fully hedged cases.

With these additions, the model could distinguish a currently unattractive spot
trade from a potentially attractive forward physical arbitrage where the future
sale price, premium, or TC/RC spread covers cost of carry.

### Fallback Assumptions

The module is designed to run even when no market CSVs or APIs are available. It
loads `copper_monte_carlo/data/default_assumptions.yaml` through
`load_default_assumptions()`. Every default in that file is editable and is labeled
as a `fallback_assumption` in the Streamlit page's input transparency table.

Current fallback examples include:

- Initial copper price: 12,000 USD/t
- Annual copper drift: 3%
- Annual copper volatility: 24%
- Initial TC: -40 USD/dmt
- Initial RC: -0.04 USD/lb
- Freight: 45 USD/wmt
- Wet tonnes: 10,000 wmt
- Copper grade: 26%
- Payable copper: 96.5%
- Hedge ratio: 80%
- All-in financing rate: 7%

If real historical data is added later, it should override these values and update
source metadata to `historical_data`, `live_data`, or `manual_user_input`.

### Running the Monte Carlo Module

From Python:

```python
from copper_monte_carlo import run_monte_carlo

result = run_monte_carlo(n_simulations=10000, horizon_months=24)
print(result.risk_summary)
```

From the dashboard:

```bash
streamlit run app.py
```

Then choose `Copper Monte Carlo Risk` from the sidebar page selector.

### Data You Can Add Later

No external data is required for the first working version. Useful future CSVs are:

- Copper price history, such as FRED `PCOPPUSDM` or project price data.
- Manual futures curve CSV.
- TC/RC history CSV.
- Freight route or index CSV.
- FX history CSV.
- LME, SHFE, or COMEX inventory CSV.

The current `data_loader.py` contains the first optional CSV hook; calibration
logic is intentionally left small so Phase 4 can be added cleanly.

### Current Limitations

Scenario comparison,
deeper basis-risk logic, manual futures curves, empirical calibration, and chart
PNG downloads are natural next steps. TC/RC and freight defaults are placeholder
estimates and should be replaced with user data for serious analysis.

## Limitations

This is an educational model, not a tool for live trading decisions. It does not include detailed assay exchange, quotational periods, provisional pricing, hedging execution, counterparty credit, insurance, taxes, final settlement, demurrage, smelter-specific blending constraints, or confidential smelter penalty schedules.

## Testing

Run the formula and risk tests with:

```bash
pytest
```

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
