# Methodology

This document explains the modeling logic used in the Copper Concentrate Trade
Economics Dashboard. The project is educational and intentionally simplified.

## 1. Cargo Quantity Logic

Copper concentrate is shipped in wet metric tonnes, but valuation is normally
based on dry metric tonnes.

```text
dry_metric_tonnes = wet_metric_tonnes * (1 - moisture)
```

Contained copper:

```text
contained_copper_tonnes = dry_metric_tonnes * copper_grade
```

Payable copper:

```text
payable_copper_tonnes = contained_copper_tonnes * payable_copper_percentage
```

The original valuation dashboard also includes a simplified deduction-unit rule
and uses the lower of percentage payability and deduction payability.

## 2. Copper Reference Price

The model does not treat concentrate and refined copper as the same product. It
uses a copper reference price to value the payable copper contained in the
concentrate.

```text
gross_copper_value = payable_copper_tonnes * copper_price_usd_per_tonne
```

Commercial deductions then convert payable metal value into estimated concentrate
or trade value.

## 3. TC/RC

Treatment charge:

```text
treatment_charge = dry_metric_tonnes * tc_usd_per_dmt
```

Refining charge:

```text
refining_charge = payable_copper_lbs * rc_usd_per_lb
```

The valuation dashboard takes RC as US cents per pound and converts it to USD.
The Monte Carlo engine stores RC directly as USD per pound.

Negative TC/RC are allowed in the Monte Carlo assumptions to represent a very
tight concentrate market.

## 4. Impurity Penalties And By-Product Credits

Impurity penalties are simplified as a mix of flat USD/dmt deductions and
illustrative threshold penalties.

Gold and silver credits are calculated from grade, payability, price, and refining
charge:

```text
payable_oz = dry_metric_tonnes * grade_g_per_tonne / 31.1034768 * payability
credit = payable_oz * price
```

## 5. Financing Cost

The deterministic valuation dashboard uses simple interest over selected financing
days.

The Monte Carlo module uses:

```text
financing_cost =
    gross_metal_value
  * all_in_financing_rate
  * working_capital_days / 360
```

Working-capital days are approximated as:

```text
sale_payment_timing_days
- purchase_payment_timing_days
+ shipping_duration_days
+ storage_duration_months * 30
```

This is a proxy for cash tied up between purchase, shipment/storage, and sale
settlement.

## 6. Monte Carlo Market Paths

The Monte Carlo module simulates monthly paths.

Copper price uses a GBM-style process:

```text
next_price = current_price * exp(monthly_return)
```

TC, RC, freight, and basis use mean reversion:

```text
next_value =
    current_value
  + speed * (long_term_mean - current_value)
  + volatility * shock
```

Freight can also include jump shocks. Shocks can be correlated through the
fallback correlation matrix.

## 7. Trade Modes

The Monte Carlo engine supports four trade modes.

### Concentrate Merchant

```text
mine / producer -> trader -> smelter
```

Margin is estimated as:

```text
simulated concentrate sale invoice
- initial concentrate purchase invoice
- logistics and carry costs
+ hedge PnL
- hedge cost
```

### Smelter Conversion

```text
buy concentrate -> process -> sell recovered refined copper
```

Margin is estimated as:

```text
recovered copper value
+ by-product credit
- concentrate purchase invoice
- processing cost
- logistics and carry costs
+ hedge PnL
- hedge cost
```

### Refined Copper Trade

```text
refined copper supplier -> trader -> end user
```

Margin is estimated as:

```text
refined sale value
- refined purchase cost
- logistics and carry costs
+ hedge PnL
- hedge cost
```

### Integrated Conversion

This preserves the initial prototype logic:

```text
buy concentrate exposure -> carry it -> sell payable copper equivalent
```

## 8. Hedge Logic

The model assumes long physical copper exposure can be hedged with a short
futures-style position.

```text
hedge_pnl =
    hedge_ratio
  * payable_copper_tonnes
  * (initial_effective_price - simulated_effective_price)
```

The hedge is deliberately simplified. It does not yet fully model futures curves,
rolls, exchange margin calls, or QP timing.

## 9. Risk Metrics

The Monte Carlo module calculates final margin distributions and summary metrics:

- Expected margin
- Median margin
- P5/P95 margin
- Probability of loss
- 95% VaR
- 95% CVaR
- Maximum drawdown
- Hedge effectiveness

VaR is reported as a positive downside loss number:

```text
VaR95 = max(0, -P5_margin)
```

CVaR is the average loss in the worst 5% tail.

## 10. Limitations

The model does not yet include:

- Full futures curves
- Full forward physical sale pricing
- Quotational-period pricing
- Separate purchase and sale TC/RC books
- Route-specific freight
- Detailed smelter penalty schedules
- Hedge roll and margin-call liquidity
- Counterparty credit risk
- Multi-cargo portfolio aggregation

These are natural extensions if the project is developed further.
