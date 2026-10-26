# PriceUnmask

PriceUnmask is a product-price monitoring and fake-discount detection application.
It collects product prices and stores price history so users can examine price changes over time.
It uses price-history analysis to help users assess discount credibility and identify unusual price changes.

## Features

- Product dashboard with search and product details
- Historical price charts
- Trust Scores: genuine, uncertain, likely inflated, or insufficient data
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

If `.env` already exists, keep your existing configuration instead of overwriting it.

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
python -m backend.devtools.seed_fake_data
uvicorn backend.main:app --reload
```

Open the application:

- Dashboard: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- API documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Health check: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

The seed command supplies three demo products for local development.

## Running with real data

The collector fetches product listings from its configured target website, saves price snapshots, and records scrape runs. It runs immediately at startup and then repeats at the configured interval, which defaults to four hours.

To start the collector:

```powershell
python -m backend.scheduler.jobs
```

The dashboard also provides a **Run now** button for manually triggering a collection.

See the [Collector runbook](docs/COLLECTOR.md) for configuration, scheduling, database checks, and troubleshooting.

## Understanding results

### Trust Score

Trust Scores help users assess discount credibility using historical price signals.

- **Genuine:** Score of 70–100.
- **Uncertain:** Score of 40–69.
- **Likely inflated:** Score below 40.
- **Insufficient data:** Fewer than six price snapshots.

### Anomaly badges

The application reports whether a price change appears normal, unusual, or cannot be assessed because there is insufficient history.

- **No anomaly detected:** No unusual change was detected from the available history.
- **Unusual price:** An unusual price change was detected.
- **Not enough data:** There is insufficient history to detect unusual price changes.

## Running tests

Run from the repository root:

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

## Team

Use the repository's GitHub issues and pull requests to discuss changes and request code review.