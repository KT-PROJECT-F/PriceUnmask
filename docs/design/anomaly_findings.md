# Anomaly findings on collected prices

## Dataset and method

Analyzed the exported SQLite database `priceunmask-20261019.db`.
The file is kept under `data/exports/` locally and is ignored by Git.

The report runner follows the API path for each product: `crud.get_history`,
`snapshots_to_dataframe`, then `detect_anomalies`. Product enumeration and
history reads go through `backend.db.crud`; the runner executes no SQL itself.
The model was not changed for this analysis.

Re-run from the repository root in PowerShell with the exported database at the
same path:

```powershell
$env:DATABASE_URL='sqlite:///data/exports/priceunmask-20261019.db'; .\.venv\Scripts\python.exe -m backend.devtools.anomaly_report; $code=$LASTEXITCODE; Remove-Item Env:\DATABASE_URL; if ($code -ne 0) { exit $code }
```

On macOS or Linux:

```bash
DATABASE_URL='sqlite:///data/exports/priceunmask-20261019.db' python -m backend.devtools.anomaly_report
```

## Results

| Measure | Result |
| --- | ---: |
| Products analyzed | 20 / 20 |
| Snapshots per product | min 40, median 40, max 40 |
| Products with too little history (5 or fewer snapshots) | 0 |
| Products with any observed price change | 0 |
| Products flagged at least once | 0 |
| Products whose latest price is flagged | 0 |
| Flagged snapshots | 0 |
| Scoreable rows | 700 (35 per product) |

The 40 snapshots per product span 2026-10-08 12:02:54 UTC through
2026-10-15 15:34:52 UTC, about 7 days, 3 hours, and 32 minutes. With a
five-price rolling window, the first five snapshots are the baseline and
cannot be scored; each product has 35 subsequent scoreable rows. Despite this
longer collection span, prices did not move.

## Worked examples

There is **no flagged product** in this export, so a real flagged example cannot
be shown without inventing a price or altering the data. Instead, these are two
actual, never-flagged examples. In both, every one of the 40 observed prices was
identical.

### A Light in the Attic

- Source and currency: `books-toscrape`, GBP
- All 40 observed prices: GBP 51.77
- Row evaluated: 2026-10-15 15:34:52 UTC; current price GBP 51.77
- Prior five prices: GBP 51.77, GBP 51.77, GBP 51.77, GBP 51.77, GBP 51.77
- Mean: 5,177 pence = GBP 51.77
- Sample standard deviation: 0 pence
- z-score: undefined because the prior window is flat
- Flat-window rule: the price differs from the baseline by 0%, below the
  required 10%; not flagged

### It's Only the Himalayas

- Source and currency: `books-toscrape`, GBP
- All 40 observed prices: GBP 45.17
- Row evaluated: 2026-10-15 15:34:52 UTC; current price GBP 45.17
- Prior five prices: GBP 45.17, GBP 45.17, GBP 45.17, GBP 45.17, GBP 45.17
- Mean: 4,517 pence = GBP 45.17
- Sample standard deviation: 0 pence
- z-score: undefined because the prior window is flat
- Flat-window rule: the price differs from the baseline by 0%, below the
  required 10%; not flagged

## Threshold assessment

Across 7 days, 3 hours, and 32 minutes of collection, none of the 20 books
changed price. Books to Scrape is a practice site with fixed prices, so the
model has nothing to flag here. We cannot judge the threshold on this data, and
the "Unusual price" badge will never show for these products. To test the
threshold, we need a source where prices really change.

## Interim re-check - 4 November 2026

A follow-up report was run using
`data/exports/priceunmask-20261026T080206Z.db`.

This is a preliminary check only. The database contains no Croma
price snapshots and does not satisfy the real-price-change validation
required by issue #226.

| Measure | Result |
| --- | ---: |
| Products analyzed | 60 / 60 |
| Snapshots per product | min 2, median 2, max 42 |
| Products with too little history | 40 |
| Products with observed price changes | 0 |
| Products flagged at least once | 0 |
| Products whose latest price is flagged | 0 |
| Total flagged snapshots | 0 |
| Scoreable rows | 740 |

Observed snapshot span (UTC):
2026-10-08T12:02:54.423369Z to 2026-10-26T07:51:38.115010Z.

No flagged example exists in this export. Two real never-flagged examples
were reported. Their prices remained constant throughout their histories.

For one 42-snapshot example, the price was GBP 51.77 throughout.
Its rolling-window standard deviation was zero, and the flat-window
rule was not met because the price change was 0%.

These results do not validate anomaly detection against genuine price
changes. A permitted source with real price movements is still required.

Re-run command:

    $env:DATABASE_URL = 'sqlite:///data/exports/priceunmask-20261026T080206Z.db'
    python -m backend.devtools.anomaly_report

## Synthetic validation - 9 November 2026

Three synthetic detector cases were already covered by existing tests:
a significant price drop, a small price increase, and a significant
price hike. This PR added one new unit test for a large drop against
a volatile baseline.

It also added a report-level integration test that seeds three
synthetic histories in SQLite and exercises the actual report
pipeline. These tests validate synthetic detector behaviour and
pipeline integration only; they are not evidence of real-world
price changes.

The detector compares each current price with the preceding five prices. For a non-flat baseline, an observation is flagged only when both conditions are met:

- Absolute percentage change is at least 10%.
- Absolute z-score is at least 3.

### Case 1: Synthetic significant price drop - flagged

Input prices: `[1000, 1010, 990, 1000, 1000, 800]`

- Baseline mean: 1000
- Sample standard deviation: approximately 7.07
- Percentage change: 20%
- Z-score: approximately -28.28

**Expected and observed result:** Flagged.

Covered by `test_detect_anomalies_flags_a_sudden_big_drop`.

### Case 2: Synthetic small price increase - not flagged

Input prices: `[1000, 1010, 990, 1000, 1000, 1030]`

- Baseline mean: 1000
- Sample standard deviation: approximately 7.07
- Percentage change: 3%
- Z-score: approximately 4.24

**Expected and observed result:** Not flagged.

The z-score threshold is met, but the percentage threshold is not.

Covered by `test_detect_anomalies_does_not_flag_a_3_percent_change`.

### Case 3: Synthetic significant price hike (increase) - flagged

Input prices: `[1000, 1010, 990, 1000, 1000, 1200]`

- Baseline mean: 1000
- Sample standard deviation: approximately 7.07
- Percentage change: 20%
- Z-score: approximately 28.28

**Expected and observed result:** Flagged.

Covered by `test_detect_anomalies_flags_an_obvious_high_spike`.

### Case 4: Synthetic large price drop with volatile baseline - not flagged

Input prices: `[700, 1300, 800, 1200, 1000, 700]`

- Baseline mean: 1000
- Sample standard deviation: approximately 254.95
- Current price: 700
- Percentage change: 30%
- Z-score: approximately -1.18

**Expected and observed result:** Not flagged.

The 30% drop passes the percentage threshold, but the absolute z-score is below 3. This demonstrates that the z-score condition independently prevents an anomaly from being flagged.

Covered by `test_detect_anomalies_does_not_flag_large_drop_with_volatile_baseline`.

### Reproducing the checks

Run the focused synthetic detector and report integration tests:

    python -m pytest tests/test_anomaly_model.py tests/test_anomaly_report.py -v

Run the full test suite:

    python -m pytest -v

### Interpretation and limitation

The synthetic cases demonstrate that significant price drops and
increases are flagged when both thresholds pass. A 3% increase is
not flagged because it does not meet the percentage threshold. A
30% drop against a volatile baseline is not flagged because its
z-score remains below 3.

This is controlled synthetic behavioural validation only. The collected
Books to Scrape exports contain no observed price movements, so
validation against genuine real-world price changes remains outstanding.

### Report-level synthetic integration test

Added `test_report_processes_synthetic_histories_from_sqlite` in
`tests/test_anomaly_report.py`.

The test seeds an isolated SQLite database with three synthetic
product histories and executes the actual `anomaly_report.report()`
pipeline. This exercises product enumeration, database history
retrieval, snapshot-to-DataFrame conversion, and anomaly detection.

Expected outcomes:

- Significant price drop: flagged.
- Significant price hike: flagged.
- Volatile baseline: not flagged.

This confirms that the report pipeline processes these controlled
synthetic histories as expected. It does not establish real-world
anomaly detection accuracy; validation against real price changes
remains outstanding.

## IsolationForest comparison - 11 November 2026

The rolling z-score detector and an exploratory IsolationForest comparison were evaluated using the same four synthetic fixtures.

### Configuration

| Setting | Value | Rationale |
| --- | --- | --- |
| Estimator | IsolationForest | Exploratory comparison |
| n_estimators | 100 | Fixed estimator count |
| contamination | 0.2 | Sets the expected outlier proportion in the five training baseline observations |
| random_state | 0, 21, 42, 99 | Checks prediction sensitivity to random initialization |
| Training data | First five prices for each product | Uses that product's own price history |
| Prediction data | Latest sixth price | Scores the latest observation against its product baseline |
| Features | Raw price | One feature per model |

Each IsolationForest model was fitted independently on one fixture's five baseline prices. Only that fixture's latest price was passed to predict().

The contamination value of 0.2 sets the decision threshold based on the training data. It does not force a fixed number of the four latest test observations to be classified as anomalies.

### Comparison results

| Synthetic fixture | Expected | Rolling z-score | IF seed 0 | IF seed 21 | IF seed 42 | IF seed 99 |
| --- | --- | --- | --- | --- | --- | --- |
| Significant drop | Anomaly | Flagged | Not flagged | Not flagged | Flagged | Not flagged |
| Small increase | Normal | Not flagged | Flagged | Flagged | Not flagged | Flagged |
| Significant hike | Anomaly | Flagged | Flagged | Flagged | Not flagged | Flagged |
| Volatile baseline | Normal | Not flagged | Not flagged | Flagged | Flagged | Not flagged |

### Metrics

| Metric | Rolling z-score | IF seed 0 | IF seed 21 | IF seed 42 | IF seed 99 |
| --- | ---: | ---: | ---: | ---: | ---: |
| True positives | 2 | 1 | 1 | 1 | 1 |
| Misses | 0 | 1 | 1 | 1 | 1 |
| False alarms | 0 | 1 | 2 | 1 | 1 |
| True negatives | 2 | 1 | 0 | 1 | 1 |

### Interpretation and decision

The rolling z-score detector correctly classified all four synthetic fixtures: both significant price changes were flagged, and both normal cases were left unflagged.

IsolationForest produced inconsistent predictions across the four random states. IsolationForest flagged the significant drop in one of four runs (random_state=42) and missed it in the other three. It flagged the significant hike in three of four runs and missed it at random_state=42. It also incorrectly flagged the small increase in three runs and the volatile-baseline case in two runs. A follow-up score_samples check on the significant-drop baseline returned identical scores for prices 1200 and 5000 at every tested random state; each pair also received the same prediction, showing that this small one-feature experiment did not distinguish the two out-of-range values.

Fitting a separate model for each product avoids mixing unrelated product prices. However, each model still has only five baseline observations, which is too little data to establish a reliable anomaly pattern. The changes across random states also show that predictions are sensitive to model initialization in this small-data setting.

The contamination parameter controls the decision threshold relative to the training baseline. It does not guarantee that the latest price will be classified correctly.

**Recommendation: Keep the rolling z-score detector.** It performed consistently on these four controlled fixtures and remains simpler to interpret. Do not replace the production detector with IsolationForest based on this limited experiment.

This is exploratory synthetic evaluation, not independent validation or evidence of real-world accuracy. A larger independent dataset containing genuine price changes is required before reconsidering the detector.

The live implementation in `backend/analysis/anomaly_model.py` was not changed as part of this comparison.
