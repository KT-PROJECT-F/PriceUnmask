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

Two controlled synthetic price histories were tested to verify the anomaly
detector's behaviour. These are constructed fixtures, not prices collected
from a commercial website. This is synthetic behavioural validation only.

The detector compares each price with the five immediately preceding prices.
For a non-flat baseline, both conditions must hold:
- Absolute percentage change is at least 10%.
- Absolute z-score is at least 3.

### Case 1: Synthetic price drop - flagged

Input prices (minor currency units):

`[1000, 1010, 990, 1000, 1000, 800]`

The first five prices form the baseline.

- Baseline mean: (1000 + 1010 + 990 + 1000 + 1000) / 5 = 1000
- Sample standard deviation: sqrt(50) approximately 7.07
- Current price: 800
- Percentage change: |800 - 1000| / 1000 * 100 = 20%
- Z-score: (800 - 1000) / 7.07 approximately -28.28
- Both thresholds are satisfied: 20% >= 10% and |-28.28| >= 3.

**Expected and observed result:** Flagged.

The detector returned `2026-10-06T00:00:00Z` in
`anomalous_timestamps`, and `latest_is_anomalous` was `True`.

### Case 2: Synthetic small price increase - not flagged

Input prices (minor currency units):

`[1000, 1010, 990, 1000, 1000, 1030]`

The first five prices form the baseline.

- Baseline mean: 1000
- Sample standard deviation: sqrt(50) approximately 7.07
- Current price: 1030
- Percentage change: |1030 - 1000| / 1000 * 100 = 3%
- Z-score: (1030 - 1000) / 7.07 approximately 4.24
- The z-score exceeds 3, but the percentage change is below 10%.

**Expected and observed result:** Not flagged.

The detector returned an empty `anomalous_timestamps` list, and
`latest_is_anomalous` was `False`.

### Case 3: Synthetic significant price increase - flagged

Input prices (minor currency units):

`[1000, 1010, 990, 1000, 1000, 1200]`

The first five prices form the baseline.

- Baseline mean: 1000
- Sample standard deviation: sqrt(50) approximately 7.07
- Current price: 1200
- Percentage change: |1200 - 1000| / 1000 * 100 = 20%
- Z-score: (1200 - 1000) / 7.07 approximately 28.28
- Both thresholds are satisfied: 20% >= 10% and |28.28| >= 3.

**Expected and observed result:** Flagged.

The detector returned `2026-10-06T00:00:00Z` in `anomalous_timestamps`, and `latest_is_anomalous` was `True`.

Covered by the existing test:
`test_detect_anomalies_flags_an_obvious_high_spike`.

### Test execution

The existing anomaly model tests cover all three synthetic behaviours:

- `test_detect_anomalies_flags_a_sudden_big_drop`
- `test_detect_anomalies_does_not_flag_a_3_percent_change`
- `test_detect_anomalies_flags_an_obvious_high_spike`

Full test suite:

Command: `python -m pytest -v`

Result: **354 passed, 1 warning**.

### Interpretation and limitation

These tests confirm that the implementation follows its configured thresholds
for the two controlled examples. A sufficiently large drop is flagged, while
a 3% movement is not flagged even when its z-score exceeds 3.

This does not establish precision, recall, false-positive rates, or reliability
on real retail price histories. The real-world validation limitation above
remains open until a permitted source with genuine price movements can be
evaluated.
