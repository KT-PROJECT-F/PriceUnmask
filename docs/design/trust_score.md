# Trust Score Design Note

## What it does
The Trust Score evaluates a claimed discount using the product's price history. It starts at 100 and deducts points for explainable warning signals. The final score maps to `genuine` (70-100), `uncertain` (40-69), or `likely_inflated` (0-39). If fewer than six snapshots exist, the score is `null` with the `insufficient_data` label. If the latest snapshot has no valid discount claim, the score is `null` with the `no_discount` label.

## Decisions

- **Rules, not a trained model:** Each threshold and deduction is explicit, deterministic, and paired with a human-readable reason. Instead of a trained model, because the available labeled examples are limited and a learned result would be harder to explain.
- **Six snapshots minimum:** A score needs enough observations to assess price behaviour; shorter histories are labelled `insufficient_data`. Instead of scoring with fewer observations, because a short history may not show a reliable trend.
- **No score without a discount claim:** If the latest original price is absent, zero, equal to, or below the current price, there is no valid discount claim; return `no_discount` and a `null` score. Instead of assigning a default numeric score, because there is no current claim to evaluate.
- **Only the latest original price counts:** The label judges the offer represented by the latest snapshot. Instead of falling back to an older discount claim, because an old offer may not describe today's price.
- **Explainable deductions:** Apply explicit penalties only when signals cross defined thresholds, and keep the result between 0 and 100. Instead of an opaque combined formula, because shoppers and reviewers should be able to understand each deduction.
The rules and thresholds are documented in [trust_score.py:24-36](../../backend/analysis/trust_score.py#L24-L36). Histories below the snapshot minimum return `insufficient_data` at [trust_score.py:159](../../backend/analysis/trust_score.py#L159); histories with enough snapshots but no valid latest claim return `no_discount` at [trust_score.py:175](../../backend/analysis/trust_score.py#L175).

## Worked example: the Demo Air Fryer
The seeded fake-discount example starts at 100 and applies these deductions:

| Signal | Air Fryer value | Threshold | Points |
|---|---:|---:|---:|
| Spike before discount | 199% | 50% | -40 |
| Discount gap | 70.0 percentage points | 30 percentage points | -25 |
| Volatility | 56.7% | 30% | -15 |
Calculation: `100 - 40 - 25 - 15 = 20`. The result is `likely_inflated`, with three explanatory reasons.

## How it is tested

- `test_compute_trust_score_seeded_fake_discount_is_exactly_20` ([tests/test_trust_score.py:722](../../tests/test_trust_score.py#L722)) verifies that the seeded fake-discount history gets score 20 from the three penalties above.
- `test_compute_trust_score_snapshot_count_boundary` ([tests/test_trust_score.py:457](../../tests/test_trust_score.py#L457)) verifies that five snapshots return `insufficient_data`, while six snapshots with no claim return `no_discount`.
- `test_compute_trust_score_ignores_older_discount_when_latest_has_no_claim` ([tests/test_trust_score.py:557](../../tests/test_trust_score.py#L557)) verifies that an older original price does not override the latest snapshot's missing claim.
The broader suite also covers seeded stable and real-drop histories, discount-gap thresholds, price-above-lowest and volatility penalties, and shopper-readable reasons.

## Known limits and what we would do next
The Trust Score uses hand-written thresholds and depends on the available history; it cannot prove seller intent or guarantee a discount is genuine. Saidivya's 26 Oct export contains 60 products and 920 snapshots: 40 products have 2 snapshots each and are labelled `insufficient_data`, while 20 products have 42 snapshots each and are labelled `no_discount`. No products have a recorded original price, so no numeric Trust Scores were produced. The earlier 19 Oct report (20 products) is not a substitute for this export. More reliable original-price data and broader real-world validation would help evaluate discount claims.
Related documents: [Trust Score weights](../trust-score-weights.md), [Spike thresholds](../spike-thresholds.md), [Trust Score findings](trust_score_findings.md), and [No-discount label](no_discount_label.md).
