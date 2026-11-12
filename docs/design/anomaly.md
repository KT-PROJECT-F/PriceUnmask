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

## Synthetic IsolationForest comparison decision - 12 November 2026

The exploratory comparison used four synthetic product-price fixtures.
The shared fixture values are maintained in
`backend/devtools/anomaly_fixtures.py` and reused by the comparison
script and anomaly tests.

For each fixture, IsolationForest was fitted on five baseline observations
and evaluated on the latest sixth observation, using random states
0, 21, 42, and 99. The six-snapshot minimum is an operational requirement
for this five-point training and one-point evaluation split. It is not a
statistically validated minimum; five training observations are too few
to establish a robust price distribution.

The exploratory `contamination=0.2` setting determines the decision
threshold from the training score distribution. It does not select or
remove training samples, nor does it guarantee that the latest price
will be classified as anomalous. With five training observations, the
20% fraction places the threshold around one training observation's score.
This setting has not been tuned or validated for production.

The rolling z-score detector classified all four fixtures correctly.
IsolationForest predictions varied across random states: it flagged the
significant price drop in only one of four runs and the significant hike
in three of four runs. It also produced false positives for the small
increase and volatile-baseline fixtures.

A follow-up `score_samples()` experiment used the significant-drop
baseline `[1000, 1010, 990, 1000, 1000]`. For every tested random state,
prices 800 and 990 received identical scores, while 1030, 1200, and
5000 also received identical scores.

In this one-feature experiment, the isolation trees split only on raw
price. Values beyond the same end of the training range can follow the
same outer branch and have the same path length, resulting in identical
scores despite different distances from the training range. This explains
why the small increase (1030) and significant hike (1200) received the
same score in each fitted model. It is an observed property of these
fitted trees, not a universal rule for every IsolationForest model.

The identical scores within each seed are distinct from random-state
sensitivity. Changing the seed changes tree partitions and can change
scores and predictions. The five-observation training baseline makes
the experiment too limited to establish reliable behaviour.

**Decision:** Retain the rolling z-score detector. This limited synthetic
experiment does not justify replacing the existing detector with
IsolationForest. Validation against genuine price changes and a larger
independent dataset would be needed before reconsidering this decision.

The production implementation in `backend/analysis/anomaly_model.py`
remains unchanged.
