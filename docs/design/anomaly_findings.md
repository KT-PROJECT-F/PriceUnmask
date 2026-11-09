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

Four controlled synthetic price histories were tested against the existing anomaly detector. These examples validate detector behaviour only; they are not evidence of real-world price changes.

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

### Case 3: Synthetic significant price increase - flagged

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

### Test execution

Run focused tests:

    python -m pytest tests/test_anomaly_model.py -v

Run the full suite:

    python -m pytest -v

### Interpretation and limitation

The synthetic cases demonstrate that the detector applies both thresholds as intended. Significant drops and increases are flagged when both thresholds pass. A 3% increase is not flagged because it does not meet the percentage threshold. A 30% drop against a volatile baseline is not flagged because its z-score remains below 3.

This is controlled synthetic behavioural validation only. The collected Books to Scrape exports contain no observed price movements, so validation against genuine real-world price changes remains outstanding.
