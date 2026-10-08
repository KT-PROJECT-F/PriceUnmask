# Trust Score weights

Date: 2026-10-07

## Decision

The score starts at 100 and subtracts named penalties for warning signals. The result is
clamped to 0–100. Scores of 70–100 are `genuine`, 40–69 are `uncertain`, and 0–39 are
`likely_inflated`. Histories shorter than six snapshots receive `insufficient_data`
instead of a numeric score.

| Warning signal | Condition | Deduction |
|---|---:|---:|
| Price spike before a claimed sale | `spike_before_discount` is true | 40 points |
| Large gap between advertised discount and real saving | Gap is at least 30 percentage points | 25 points |
| Moderate gap between advertised discount and real saving | Gap is at least 15 but below 30 percentage points | 10 points |
| Current price far above the recorded low | At least 25% above the lowest observed price | 15 points |
| High price volatility | At least 30% coefficient of variation | 15 points |

Each deduction adds a plain-English reason describing the warning. When no deduction
applies, the score includes a sentence saying that no strong warning signs were found.

## Why

A sudden pre-sale spike is the strongest direct indication of a potentially inflated
reference price, so it receives the largest single deduction. A substantial gap between
the claimed discount and the saving against earlier prices is also strong evidence;
a moderate gap receives a smaller deduction. Being far above the observed low and
unusually volatile are supporting warnings, not proof of a fake discount, so each has a
smaller penalty.

These are initial rule-based weights, calibrated so the seeded stable-price and gradual
real-drop products remain `genuine` while the seeded price-hike-then-sale product is
`likely_inflated`. They should be revisited against more real price histories and reviewed
for false positives, especially where normal promotions or lasting price changes resemble
spikes.

## Notes on the rules

`real_discount_vs_median_pct` is clamped at 0 in `compute_signals`, so a price above the
earlier median counts as "no real saving". The gap rule therefore compares the advertised
discount with 0 in that case, which makes the gap as large as the advertised discount.

A spike on its own (no gap, no volatility) costs 40 points, so the score is 60 and the label
is `uncertain`. The label `likely_inflated` needs the spike plus at least one more warning.

Least certain weight: the volatility penalty (15). A product with a normal, regular sale
cycle can look volatile without being dishonest. More real price histories are needed
to tune it.
