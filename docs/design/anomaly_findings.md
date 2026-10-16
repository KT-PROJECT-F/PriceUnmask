# Anomaly findings on collected prices

## Dataset and method

Analyzed the exported SQLite database `priceunmask-20261013T052735Z 2.db`.
The file is kept under `data/exports/` locally and is ignored by Git.

The report runner follows the API path for each product: `crud.get_history`,
`snapshots_to_dataframe`, then `detect_anomalies`. Product enumeration and
history reads go through `backend.db.crud`; the runner executes no SQL itself.
The model was not changed for this analysis.

Re-run from the repository root in PowerShell with the exported database at the
same path:

```powershell
$env:DATABASE_URL='sqlite:///data/exports/priceunmask-20261013T052735Z 2.db'; .\.venv\Scripts\python.exe -m backend.devtools.anomaly_report; $code=$LASTEXITCODE; Remove-Item Env:\DATABASE_URL; if ($code -ne 0) { exit $code }
```

## Results

| Measure | Result |
| --- | ---: |
| Products analyzed | 20 / 20 |
| Snapshots per product | min 27, median 27, max 27 |
| Products with too little history (5 or fewer snapshots) | 0 |
| Products with any observed price change | 0 |
| Products flagged at least once | 0 |
| Products whose latest price is flagged | 0 |
| Flagged snapshots | 0 |
| Scoreable rows | 440 (22 per product) |

The 27 snapshots per product span only 2026-10-12 10:41:19 UTC through
13:56:19 UTC. With a five-price rolling window, the first five snapshots are
the baseline and cannot be scored; each product has 22 subsequent scoreable
rows. The export therefore has enough rows for the calculation, but they cover
only about three hours and contain no price movement.

## Worked examples

There is **no flagged product** in this export, so a real flagged example cannot
be shown without inventing a price or altering the data. Instead, these are two
actual, never-flagged examples. In both, every one of the 27 observed prices was
identical.

### A Light in the Attic

- Source and currency: `books-toscrape`, GBP
- All 27 observed prices: GBP 51.77
- Row evaluated: 2026-10-12 13:56:19 UTC; current price GBP 51.77
- Prior five prices: GBP 51.77, GBP 51.77, GBP 51.77, GBP 51.77, GBP 51.77
- Mean: 5,177 pence = GBP 51.77
- Sample standard deviation: 0 pence
- z-score: undefined because the prior window is flat
- Flat-window rule: the price differs from the baseline by 0%, below the
  required 10%; not flagged

### It's Only the Himalayas

- Source and currency: `books-toscrape`, GBP
- All 27 observed prices: GBP 45.17
- Row evaluated: 2026-10-12 13:56:19 UTC; current price GBP 45.17
- Prior five prices: GBP 45.17, GBP 45.17, GBP 45.17, GBP 45.17, GBP 45.17
- Mean: 4,517 pence = GBP 45.17
- Sample standard deviation: 0 pence
- z-score: undefined because the prior window is flat
- Flat-window rule: the price differs from the baseline by 0%, below the
  required 10%; not flagged

## Threshold assessment

The result is **inconclusive about whether the threshold is right**. Zero flags
are consistent with these unchanged prices, not evidence that the detector
would catch genuine changes or avoid false positives on moving prices. The
current model requires at least a 10% change; for a non-flat window it also
requires an absolute rolling z-score of at least 3. For a flat window, the
10% change rule applies because a z-score is undefined.

Before trusting flags in a shopper-facing experience, collect longer histories
that include real price changes (and more than one short collection period),
then manually verify flagged rows against source prices and scrape records.
This export cannot establish the model's sensitivity: all 20 products were
unchanged over the roughly three-hour observation span.
