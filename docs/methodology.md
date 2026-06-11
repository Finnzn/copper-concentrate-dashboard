# Methodology

This document explains the simplified valuation logic used in the Copper Concentrate Trade Economics Dashboard. It is written for an educational project and does not represent a full commercial contract model.

## Wet Metric Tonnes and Dry Metric Tonnes

Copper concentrate is often weighed and shipped as wet metric tonnes, or wmt. A wet tonne includes moisture. Commercial valuation normally focuses on dry metric tonnes, or dmt, because the buyer is paying for the dry mineral material and contained metals, not the water.

The dashboard uses:

```text
dry_metric_tonnes = wet_metric_tonnes * (1 - moisture_percentage / 100)
```

## Moisture

Moisture reduces the dry quantity available for valuation. A 10,000 wmt shipment at 8% moisture contains 9,200 dmt of dry concentrate. Moisture also matters operationally because it affects handling, transport, and contract specifications.

## Contained Copper Versus Payable Copper

Contained copper is the theoretical copper metal inside the dry concentrate:

```text
contained_copper_tonnes = dry_metric_tonnes * copper_grade_percentage / 100
```

Payable copper is the portion of contained copper that is commercially paid for after metallurgical recovery and contract deductions. The dashboard models this with a simplified "lesser of" rule:

```text
payable_by_percentage = contained_copper_tonnes * payable_copper_percentage / 100
payable_by_deduction =
    dry_metric_tonnes * (copper_grade_percentage - deduction_unit_percentage) / 100

payable_copper_tonnes = min(payable_by_percentage, payable_by_deduction)
```

The LME copper price is then applied to payable copper tonnes, not directly to total concentrate tonnes.

## Treatment Charges

Treatment charges, or TC, compensate the smelter for treating the concentrate. TC is expressed in USD per dry metric tonne of concentrate, written as USD/dmt, because the cost relates to processing the bulk concentrate material.

```text
treatment_charge_usd = dry_metric_tonnes * tc_usd_per_dmt
```

## Refining Charges

Refining charges, or RC, compensate the smelter for refining the payable copper metal. RC is commonly expressed in US cents per pound of payable copper, written as US¢/lb, because it relates to the metal units being refined.

```text
refining_charge_usd = payable_copper_lb * rc_cents_per_lb / 100
```

## Unit Conversion from Tonnes to Pounds

The model uses:

```text
1 metric tonne = 2,204.62262 lb
```

This conversion is required because payable copper is first calculated in metric tonnes, while RC is charged in US cents per pound.

## Freight and Logistics Deductions

Freight and logistics costs are modeled as USD/dmt:

```text
freight_cost_usd = dry_metric_tonnes * freight_usd_per_dmt
```

This is a simplification. Real logistics economics may include ocean freight, inland transport, port costs, insurance, demurrage, laytime, storage, financing, and timing effects.

## Impurity Penalties

Some concentrates contain deleterious elements that may reduce value or limit the number of suitable smelters. The dashboard models impurity penalties as a single USD/dmt deduction:

```text
flat_impurity_penalty_usd = dry_metric_tonnes * impurity_penalty_usd_per_dmt
```

It also includes illustrative threshold penalties for arsenic, bismuth, and fluorine:

```text
element_penalty_usd =
    dry_metric_tonnes
    * max(0, assay_ppm - threshold_ppm) / 1000
    * penalty_usd_per_dmt_per_1000ppm
```

These schedules are deliberately simple and are not intended to represent a specific smelter contract.

## By-Product Credits

Some copper concentrates contain payable gold, silver, or other metals. The dashboard estimates gold and silver credits from grade, payable percentage, metal price, and refining charge:

```text
payable_oz =
    dry_metric_tonnes * grade_g_per_dmt / 31.1034768 * payable_percentage / 100

metal_credit_usd = payable_oz * (metal_price_usd_per_oz - refining_charge_usd_per_oz)
```

The model also allows an other by-product credit in USD/dmt as a catch-all simplification.

## Financing Cost

Financing cost is modeled with simple interest on positive pre-financing shipment value:

```text
financing_cost_usd =
    max(0, subtotal_before_financing_usd)
    * annual_financing_rate_percentage / 100
    * financing_days / 360
```

This is a simple working-capital proxy. A full trade finance model would need payment dates, provisional invoices, final settlement, borrowing spreads, margining, and actual cash-flow timing.

## Net Smelter Return / Estimated Shipment Value

The estimated net shipment value is calculated as:

```text
net_value_usd =
    gross_copper_value_usd
    - treatment_charge_usd
    - refining_charge_usd
    - freight_cost_usd
    - total_impurity_penalty_usd
    - financing_cost_usd
    + byproduct_credit_usd
```

The dashboard also calculates value per dry metric tonne:

```text
value_per_dmt_usd = net_value_usd / dry_metric_tonnes
```

## Limitations

This model is simplified. It does not include quotational period optionality, assay exchange, provisional pricing, final settlement, hedging, basis risk, financing costs, credit risk, VAT/tax treatment, insurance, demurrage, smelter-specific penalties, moisture loss adjustments, or detailed payable schedules for gold and silver.

It is intended to demonstrate commercial reasoning and unit discipline in physical non-ferrous metals trading, not to support live trading decisions.
