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
