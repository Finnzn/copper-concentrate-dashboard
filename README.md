# Copper Concentrate Trade Economics Dashboard

A Python and Streamlit project for exploring copper concentrate valuation,
physical copper trade economics, and market-risk simulation.

The project is educational rather than a production trading system. Its purpose
is to make the building blocks of physical non-ferrous commodity trading visible:
quality, payable metal, TC/RC, impurities, by-product credits, freight, storage,
financing, timing, and hedge risk.

## What It Does

The dashboard has two connected parts.

1. **Concentrate valuation dashboard**

   Values a copper concentrate cargo from physical and commercial assumptions:

   - Wet tonnes, moisture, dry tonnes
   - Copper grade, contained copper, payable copper
   - Copper reference price
   - Treatment charges and refining charges
   - Freight and impurity penalties
   - Gold and silver by-product credits
   - Financing cost
   - Net shipment value and value per dry tonne
   - Scenario, sensitivity, and tornado-style risk views

2. **Copper Monte Carlo Risk page**

   Simulates monthly market paths and recalculates physical trade margin under
   different trade structures:

   - Copper price paths
   - TC/RC paths
   - Freight paths
   - FX and basis paths
   - Hedge PnL
   - Margin distributions
   - Probability of loss, VaR, CVaR, and hedge effectiveness

## Why Copper Concentrate Valuation Is Specialized

Copper concentrate is not refined copper cathode. It is a physical intermediate
product with moisture, grade, impurities, payability terms, and smelter-processing
economics.

The model does **not** assume:

```text
1 tonne of concentrate = 1 tonne of copper
```

Instead, it converts concentrate into payable copper:

```text
wet concentrate tonnes
-> dry concentrate tonnes
-> contained copper tonnes
-> payable copper tonnes
-> payable copper value using a copper reference price
-> less TC/RC, freight, penalties, financing, and other costs
```

That is why two cargoes with the same gross tonnage can have very different
commercial values.

## Core Formulas

Quantity logic:

```text
dry_metric_tonnes = wet_metric_tonnes * (1 - moisture)
contained_copper_tonnes = dry_metric_tonnes * copper_grade
payable_copper_tonnes = contained_copper_tonnes * payable_copper_percentage
payable_copper_lbs = payable_copper_tonnes * 2,204.62262185
```

Valuation logic:

```text
gross_copper_value = payable_copper_tonnes * copper_price_usd_per_tonne
treatment_charge = dry_metric_tonnes * tc_usd_per_dmt
refining_charge = payable_copper_lbs * rc_usd_per_lb
freight_cost = tonnes * freight_rate
financing_cost = exposure * annual_rate * days / 360
net_value = gross_copper_value + byproduct_credits - deductions
```

TC is modeled as USD per dry metric tonne of concentrate. RC is modeled as US
cents per pound in the valuation dashboard and USD per pound in the Monte Carlo
engine.

## Monte Carlo Methods

The Monte Carlo module is path-based. It simulates full monthly paths, not just a
single end-period shock.

- Copper price uses a geometric Brownian motion style process with optional jumps.
- TC, RC, freight, and basis use mean-reverting processes.
- Freight can include jump shocks for disruption scenarios.
- FX is modeled with a simple GBM-style process.
- Shocks can be correlated through a fallback correlation matrix.

The simulation is vectorized with NumPy and loops over months rather than over
every simulation path. This keeps 10,000 simulations over a 24-month horizon
reasonable on a normal laptop.

## When The Monte Carlo Is Useful

The Monte Carlo page is most useful when the trade still has open or imperfectly
hedged exposure. It is a risk tool for understanding the distribution of possible
outcomes, not a replacement for calculating a locked physical spread.

Good applications include:

- Unpriced inventory where the sale price is not fixed yet
- Purchase and sale quotational periods that do not match
- Concentrate trades exposed to TC/RC, freight, basis, FX, or assay uncertainty
- Partially hedged positions where the hedge ratio is below 100%
- Hedges that do not exactly match the physical exposure by date, exchange,
  location, grade, premium, or quotation period
- Stress tests for copper price, TC/RC normalization, freight spikes, basis moves,
  and financing assumptions
- Downside planning through probability of loss, VaR, CVaR, and bad-tail margin
  outcomes

The current Monte Carlo is less useful for a perfectly locked carry trade. For
example, if a trader already owns copper cathode, has fixed the physical sale
price, has fixed freight or freight exposure, and all remaining costs are known,
then copper price P&L VaR should be close to zero. In that case the relevant
analysis is:

```text
locked sale price
- known purchase/value basis
- known carry, freight, storage, insurance, finance, and handling costs
= locked net margin
```

Monte Carlo still has value for that trade only if residual risks remain, such as
counterparty default, delivery delay, QP mismatch, basis/premium mismatch,
financing-rate changes, futures margin-call liquidity, quality problems, or
quantity tolerance.

## Forward Curve Versus Simulated Spot

The dashboard currently simulates future spot-style paths. A simulated future spot
price is an uncertain future outcome. A futures or forward curve is different: it
is today's tradable price for a future delivery or pricing month.

For locked physical economics, a trader normally starts with the forward curve:

```text
M6 sale price
- M3 purchase price
- cost of carry
= forward carry margin
```

If the M3/M6 spread is large enough to cover financing, storage, insurance,
warehouse costs, freight, and execution costs, the trade can be attractive even if
the current spot-style stress test looks weak.

Contango means forward prices are above nearby or spot prices. This can help an
inventory carry trade because the future sale price may compensate the cost of
holding material.

Backwardation means forward prices are below nearby or spot prices. This usually
hurts a carry trade because the future sale price may not cover the cost of
holding material.

The stronger future version of this project would use the forward curve as the
base commercial pricing layer, then use Monte Carlo to simulate residual risk
around that locked or partially locked trade.

## Trade Modes

The Monte Carlo page separates physical business models instead of mixing every
copper activity into one formula.

### Concentrate Merchant

Approximates:

```text
mine / producer -> trader -> smelter
```

The trader buys concentrate and sells concentrate. Margin depends on purchase and
sale invoice terms, payable copper, TC/RC, by-product credits, freight, financing,
and hedge effects.

### Smelter Conversion

Approximates:

```text
buy concentrate -> process it -> sell recovered refined copper
```

This mode applies a recovery rate and processing cost. It is a simplified smelter
view, not a detailed smelter operating model.

### Refined Copper Trade

Approximates:

```text
refined copper supplier -> trader -> end user
```

TC/RC and concentrate impurities are not the main economic drivers here. Premiums,
freight, storage, financing, FX, and hedge basis matter more.

### Integrated Conversion

Preserves the earlier prototype:

```text
buy concentrate exposure -> carry it -> sell payable copper equivalent
```

This is useful for broad stress testing, but the separated modes are commercially
cleaner.

## Current Assumptions

The project runs without live market data. Defaults are stored in:

```text
copper_monte_carlo/data/default_assumptions.yaml
```

Important fallback values include:

- Initial copper price: 12,000 USD/t
- Annual copper drift: 3%
- Annual copper volatility: 24%
- Initial TC: -40 USD/dmt
- Initial RC: -0.04 USD/lb
- Freight: 45 USD/wmt
- Wet tonnes: 10,000 wmt
- Moisture: 8%
- Copper grade: 26%
- Payable copper: 96.5%
- Storage duration: 2 months
- All-in financing rate: 7%
- Hedge ratio: 80%

These are transparent placeholder assumptions, not official market data.

## Interpreting Negative Margins

Negative fallback margins should not be read as a conclusion that concentrate or
refined copper trading is unattractive in general. They mean only that the current
placeholder terms do not cover the assumed freight, storage, insurance, financing,
and other carry costs.

The current model is closer to a spot-style stress test than a full forward
physical trading book. A real trader might buy material today, carry it, and sell
it forward for a future delivery month. If the future price, physical premium, or
TC/RC spread is rich enough, it can cover cost of carry.

## What Is Not Yet Modeled

The most important simplifications are:

- No full futures curve engine
- No delivery-month forward pricing
- No full quotational-period pricing
- No separate purchase and sale TC/RC books
- No route-specific freight model
- No detailed smelter penalty schedules
- No hedge roll or exchange margin-call logic
- No counterparty credit model
- No multi-cargo portfolio view

These limitations are deliberate areas for future improvement.

## Future Extensions

Useful next additions would be:

- Manual futures curve input by delivery month
- Synthetic futures curves from spot plus carry
- Contango/backwardation scenario controls
- Purchase month, shipment month, arrival month, and delivery month
- Forward physical sale contracts
- Separate purchase and sale TC/RC terms
- Regional physical premiums by month and destination
- LME cash, LME 3M, COMEX, and manual reference-price selection
- QP rules such as M, M+1, M+2, and monthly averages
- Hedge entry/exit month tied to the physical pricing period
- Hedge roll cost or benefit
- Side-by-side scenario comparison tables

With these additions, the model could distinguish an unattractive spot-style trade
from a potentially attractive forward physical arbitrage.

## Project Structure

```text
copper-concentrate-dashboard/
├── app.py
├── README.md
├── requirements.txt
├── copper_monte_carlo/
│   ├── app_integration.py
│   ├── concentrate_valuation.py
│   ├── config.py
│   ├── data_loader.py
│   ├── plots.py
│   ├── risk_metrics.py
│   ├── simulation_engine.py
│   ├── stochastic_processes.py
│   └── data/default_assumptions.yaml
├── data/
│   ├── sample_concentrate_specs.csv
│   └── sample_lme_prices.csv
├── docs/
│   └── methodology.md
├── src/
│   ├── risk.py
│   ├── scenarios.py
│   └── valuation.py
└── tests/
    ├── test_monte_carlo.py
    └── test_valuation.py
```

`docs/private_project_summary.md` is intentionally ignored by git and used only
as private interview prep.

## Installation

```bash
pip install -r requirements.txt
```

Run the app:

```bash
streamlit run app.py
```

Or:

```bash
python3 -m streamlit run app.py
```

Then choose either `Concentrate Valuation` or `Copper Monte Carlo Risk` in the
sidebar.

## Testing

```bash
python3 -m pytest -q
```

The tests cover deterministic valuation formulas, risk metrics, probability
bounds, VaR/CVaR consistency, zero-volatility behavior, hedge variance reduction,
and all Monte Carlo trade modes.

## Disclaimer

This is a simplified educational model built to explore physical non-ferrous
commodity economics. It uses illustrative assumptions and should not be used for
commercial trading decisions.
