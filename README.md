# PriceUnmask

PriceUnmask is a product-price monitoring and fake-discount detection application.

Tracks product prices over time and evaluates whether discounts look genuine using price history, Trust Scores, and anomaly detection.

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

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}

python -m backend.devtools.seed_fake_data
uvicorn backend.main:app --reload
```

If `.env` already exists, keep your existing configuration instead of overwriting it.

### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

if [ ! -f .env ]; then
    cp .env.example .env
fi

python -m backend.devtools.seed_fake_data
uvicorn backend.main:app --reload
```

Open the application:

- Dashboard: http://127.0.0.1:8000/
- API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/health

The seed command creates three synthetic demo products for local development. It exits if fake data has already been seeded in the configured database.

## Running with real data

The collector fetches product listings from its configured target website, saves price snapshots, and records scrape runs. It runs immediately at startup and then repeats at the configured interval, which defaults to four hours.

To start the collector:

```powershell
python -m backend.scheduler.jobs
```

The dashboard also provides a **Run now** button for manually triggering a collection.

### Database configuration

The application uses `data/priceunmask.db` by default. The demo seeder writes its three synthetic products to the database configured by `DATABASE_URL`.

The collector runbook documents Saidivya's live collector using `data/collector.db` for real collected data, without demo seed data. This separation depends on the database configuration; verify `DATABASE_URL` before running the seeder or collector.

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
