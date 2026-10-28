# PriceUnmask

PriceUnmask tracks product prices over time and tells you whether a "discount" is real, using the product's own price history: a Trust Score and an anomaly badge for every product.

## Features

- Product dashboard with search and product details
- Historical price charts
- Trust Scores for assessing discount credibility
- Anomaly badges for unusual price changes
- Automated product-price collection and scrape-run tracking

## Quick start

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
Copy-Item .env.example .env

python -m backend.devtools.seed_fake_data
uvicorn backend.main:app --reload
```

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env

python -m backend.devtools.seed_fake_data
uvicorn backend.main:app --reload
```

Already have a `.env`? Skip the `Copy-Item` (or `cp`) line, it would overwrite your settings.

Open the application:

- Dashboard: http://127.0.0.1:8000/
- API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

The seed command creates three synthetic demo products for local development. It exits if fake data has already been seeded in the configured database.

## Running with real data

The collector fetches the listing pages set by `SCRAPE_TARGET_URL` in `.env`, saves a price snapshot for every product, and records each run in `scrape_runs`. It runs once at startup, then every `SCRAPE_INTERVAL_HOURS` (default 4).

Keep real data apart from the three demo products by giving it its own database file. In the same terminal:

```powershell
$env:DATABASE_URL = "sqlite:///data/collector.db"
python -m backend.scheduler.jobs
```

Stop it with **Ctrl+C**. Without `DATABASE_URL`, the collector writes to `data/priceunmask.db`, next to the demo products.

To see the real data on the dashboard, start the app in a terminal with the same `DATABASE_URL`. The **Run now** button on the dashboard starts one collection straight away.

For health checks, exports, the live collector and troubleshooting, see the [Collector runbook](docs/COLLECTOR.md).

## Understanding results

### Trust Score

Trust Scores help users assess discount credibility using historical price signals.

- **Genuine:** Score of 70–100.
- **Uncertain:** Score of 40–69.
- **Likely inflated:** Score below 40.
- **Insufficient data:** Fewer than six price snapshots.
- **No discount to judge (`no_discount`):** At least six price snapshots are available, but the latest snapshot has no valid discount claim. The score is `null` because there is no discount to evaluate.

A valid discount claim requires an original price that is present, positive, and strictly greater than the current price.

For `no_discount`, the badge reads **No discount to judge**, the message is **The latest price has no discount to evaluate.**, and the reason explains the missing valid discount claim.


### Anomaly badges

The application reports whether a price change appears normal, unusual, or cannot be assessed because there is insufficient history.

- **No anomaly detected:** No unusual change was detected from the available history.
- **Unusual price:** An unusual price change was detected.
- **Not enough data:** There is insufficient history to detect unusual price changes.

## Running tests

Run from the repository root with the virtual environment activated:

```powershell
ruff check .
ruff format --check .
pytest -q
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — system design, API, data model, and analysis.
- [Collector runbook](docs/COLLECTOR.md) — collector setup, scheduling, and troubleshooting.
- [Release checklist](docs/RELEASE_CHECKLIST.md) — fresh-clone release verification.
- [Contributing guide](CONTRIBUTING.md) — branches, pull requests, and reviews.
