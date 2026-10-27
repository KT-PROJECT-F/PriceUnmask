# Trust Score Design Note



## What it does



The Trust Score evaluates a claimed discount using the product's price history. It starts at 100 and deducts points for explainable warning signals. The final score maps to `genuine` (70-100), `uncertain` (40-69), or `likely_inflated` (0-39). If fewer than six snapshots exist, the score is `null` with the `insufficient_data` label. If the latest snapshot has no valid discount claim, the score is `null` with the `no_discount` label.



## Decisions



- **Rules, not a trained model:** Each deduction has an explicit threshold and a human-readable reason, making the result easier to explain.

- **Six snapshots minimum:** A score needs enough observations to assess price behaviour. Shorter histories are labelled `insufficient_data`.

- **No score without a discount claim:** Without a valid latest original price above the current price, there is no discount to evaluate. The result is `no_discount` with a `null` score.

- **Only the latest original price counts:** The current claim is what shoppers need evaluated; older original prices do not establish that today's discount is genuine.

- **Explainable deductions:** Penalties are applied when defined signals cross their thresholds. The score is bounded between 0 and 100.



## Worked example: the Demo Air Fryer



The seeded fake-discount test starts at 100 points and applies three deductions:



- **40 points - price spike:** The price rose sharply before the sale.

- **25 points - large discount gap:** The advertised discount exceeds the saving against the earlier typical price by at least 30 percentage points. In the seeded example, the gap is 70 percentage points.

- **15 points - high volatility:** Prices varied substantially, meeting the 30% volatility threshold.



Calculation: `100 - 40 - 25 - 15 = 20`.



The result is `likely_inflated`, with three explanatory reasons. Test proof: `test_compute_trust_score_seeded_fake_discount_is_exactly_20` in `tests/test_trust_score.py`.



## How it is tested



The tests cover seeded stable, real-drop, and fake-discount histories; the exact Air Fryer score of 20; the six-snapshot minimum; discount-gap thresholds; price-above-lowest and volatility penalties; and shopper-readable reasons. The implementation is in [backend/analysis/trust_score.py](../../backend/analysis/trust_score.py).



## Known limits and what we would do next



The score uses hand-written thresholds and depends on the available history; it cannot prove seller intent or guarantee a discount is genuine. The current export report found 20 products with no recorded original price, so all 20 received `no_discount` and no numeric score. Better source data containing reliable original prices and broader real-world validation would help evaluate discount claims.



Related documents: [Trust Score weights](../trust-score-weights.md), [Spike thresholds](../spike-thresholds.md), [Trust Score findings](trust_score_findings.md), and [No-discount label](no_discount_label.md).
