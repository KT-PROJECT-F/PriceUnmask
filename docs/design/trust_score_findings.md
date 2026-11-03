# Trust Score findings on collected prices

## Dataset and method

Analyzed the exported SQLite database `priceunmask-20261019.db`, provided by Saidivya,
kept locally under `data/exports/` and ignored by Git.

The analysis follows the API-equivalent history path for each product:
`crud.get_history`, `snapshots_to_dataframe`, then `compute_trust_score`.
Product enumeration and history reads go through `backend.db.crud`; no SQL
was executed directly. The Trust Score model was not changed.

## Results

| Measure | Result |
| --- | ---: |
| Products analyzed | 20 / 20 |
| Total snapshots | 800 |
| Snapshots per product | 40 |
| Products with any recorded original price | 0 |
| Products labeled `genuine` | 20 |
| Products labeled with another category | 0 |
| Products with score 100 | 20 |

All 800 snapshots belong to histories with 40 observations per product.
The observed histories span approximately 7.15 days. No product had a recorded
`original_price_minor` value, so the dataset contains no recorded original-price
evidence from which to assess a claimed discount.

## Worked examples

Both examples are actual results from the collected dataset. Their prices
remained constant across all 40 snapshots.

### A Light in the Attic

- Product ID: `1`
- Source and currency: `books-toscrape`, GBP
- All 40 observed prices: GBP 51.77 (5,177 pence)
- Score: `100`
- Label: `genuine`
- Reason: "The recorded prices show no strong signs of an inflated discount."
- Days of history: approximately 7.15
- Lowest recorded price: 5,177 pence
- Price volatility: 0%
- Price above lowest: 0%
- Claimed discount: unavailable (`None`)
- Spike before discount: `False`

### It's Only the Himalayas

- Product ID: `20`
- Source and currency: `books-toscrape`, GBP
- All 40 observed prices: GBP 45.17 (4,517 pence)
- Score: `100`
- Label: `genuine`
- Reason: "The recorded prices show no strong signs of an inflated discount."
- Days of history: approximately 7.15
- Lowest recorded price: 4,517 pence
- Price volatility: 0%
- Price above lowest: 0%
- Claimed discount: unavailable (`None`)
- Spike before discount: `False`

## Interpretation and recommendation

All products received a score of 100 because the recorded histories are flat
and contain no observed signs of an inflated discount. However, none of these
products has a recorded original/strikethrough price.

The result describes the evidence available to the scoring model; it does not
prove that a product is authentic, that its regular price is fair, or that a
discount is genuine. In this dataset, the reason "no strong signs of an
inflated discount" should not be interpreted as proof of authenticity.

**Recommendation:** Review whether the `genuine` label is appropriate when no
discount has ever been observed or no original price is available. A neutral
label such as "insufficient discount evidence" may communicate this limitation
more clearly. This is a recommendation only; no scoring code or contract was
changed as part of this analysis.

The dataset is also limited for evaluating detection quality: the recorded
prices do not change, and there are no original-price values. A more informative
evaluation needs collected histories with price changes and observed discount
claims, including examples where the claimed original price can be compared
with prior prices.
## Reproducibility

Run from the repository root with the exported database at
`data/exports/priceunmask-20261019.db`.

PowerShell command:

    $env:DATABASE_URL = 'sqlite:///data/exports/priceunmask-20261019.db'
    python -m backend.devtools.trust_score_report

macOS or Linux command:

    DATABASE_URL='sqlite:///data/exports/priceunmask-20261019.db' python -m backend.devtools.trust_score_report

The runner enumerates products through `crud.list_products`, reads histories
through `crud.get_history`, converts them with `snapshots_to_dataframe`,
and calls `compute_trust_score`. It does not execute SQL directly. Summary
logic is covered by `tests/test_trust_score_report.py`.
