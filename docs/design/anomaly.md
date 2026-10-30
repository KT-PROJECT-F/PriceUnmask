# Anomaly Detection Design Note

## What it does

The anomaly detector checks a product's price history for unusually large changes.
It compares each price with the five immediately preceding snapshots, using a rolling z-score and a minimum percentage-change rule.
It returns the timestamps of flagged snapshots and a separate boolean indicating whether the latest snapshot is anomalous.
This is a statistical warning, not proof that a discount is genuine or fake; it runs alongside the existing rules rather than replacing them.

Implementation: [anomaly_model.py](../../backend/analysis/anomaly_model.py#L34-L119).

## Decisions

- **Start with a rolling z-score.** It is explainable and compares a price only with earlier observations. IsolationForest is a possible future option, not the current detector; we need more meaningful changing-price history before adding model complexity. See the [implementation notes](../../backend/analysis/anomaly_model.py#L1-L5).
- **Use five preceding snapshots and a z-score threshold of 3.0.** Five observations provide a small local baseline. A z-score of 3 means the observed price is three standard deviations from that baseline's mean; the detector uses the absolute value so unusually large increases and decreases can qualify. These settings are initial heuristics, not a guarantee of accuracy. See [the constants and calculation](../../backend/analysis/anomaly_model.py#L12-L31).
- **Require a change of at least 10%.** For a non-flat baseline, both the 10% change rule and an absolute z-score of at least 3 must be satisfied. For a flat baseline, the standard deviation is zero, so the z-score is undefined; the detector instead applies the 10% rule. This avoids treating tiny changes as anomalies. See [the flagging rules](../../backend/analysis/anomaly_model.py#L82-L95).
- **Require at least six snapshots to score a price.** The first five establish the baseline; the sixth is the first price that can be compared with a complete prior window. Empty and short histories return no flagged timestamps. See [history validation](../../backend/analysis/anomaly_model.py#L43-L69).
- **Keep diagnostic notes separate from shopper-facing messages.** The result's `note` explains the detector's outcome for internal analysis. Shopper-facing statuses and wording are documented separately in [Anomaly Messages](anomaly_messages.md); the note should not be presented as the shopper message.

## Worked example

The test `test_detect_anomalies_flags_an_obvious_high_spike` uses this history, in chronological order:

`[1000, 1010, 990, 1000, 1000, 1200]`

1. The first five prices form the baseline: 1000, 1010, 990, 1000, and 1000.
2. Their mean is 1000. Their sample standard deviation is approximately 7.07.
3. The sixth price is 1200, which is 200 above the mean: `(1200 - 1000) / 1000 × 100 = 20%`.
4. Its z-score is approximately `(1200 - 1000) / 7.07 = 28.28`. The change exceeds 10%, and the absolute z-score exceeds 3, so the detector flags this snapshot.
5. The test expects the timestamp `2026-10-06T00:00:00Z` and `latest_is_anomalous = True`.

See the [worked-example test](../../tests/test_anomaly_model.py#L73-L81) and [rolling calculation and flagging logic](../../backend/analysis/anomaly_model.py#L71-L100).

## How it is tested

The unit tests cover empty and short histories, unchanged prices, a jump after a flat baseline, small changes below 10%, a high spike, a sudden drop, a slow steady rise, the difference between a past anomaly and the latest status, and chronological ordering with UTC timestamps. These tests check the detector's defined behavior; they do not establish its accuracy on real changing prices.

See [test_anomaly_model.py](../../tests/test_anomaly_model.py).

## Known limits and what we would do next

The collected Books to Scrape report analyzed 20 products with 40 snapshots per product. None of the products changed price, and no snapshots were flagged. Because all observed prices stayed fixed, these results cannot tell us whether the detector will reliably identify genuine unusual changes on a changing-price source.

For these collected products, the latest prices have enough history and are not flagged, so the anomaly status is normal—not unusual. That is consistent with the observed data, but it does not validate the detector against real price movements.

Next, collect longer histories from a source whose prices actually change, evaluate known increases and decreases, and review false positives and missed changes before adjusting the window or thresholds. Consider IsolationForest only when the amount and quality of data justify comparing it with the simpler baseline.

See [Anomaly Findings](anomaly_findings.md) for the collected-data results and [Anomaly Messages](anomaly_messages.md) for the shopper-facing statuses.
