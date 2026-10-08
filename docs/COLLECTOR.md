# Collector (draft)

The collector runs a scrape immediately after startup, then repeats every
`SCRAPE_INTERVAL_HOURS` (4 hours by default). It writes runs and price snapshots
to the database configured by `DATABASE_URL` (by default,
`data/priceunmask.db`).

## Start

From the repository root, activate the project environment and run:

```powershell
.\.venv\Scripts\Activate.ps1
python -m backend.scheduler.jobs
```

Set `SCRAPE_TARGET_URL` in the environment or `.env` to the listing page to
scrape. The process logs each cycle to the terminal with a timestamp and log
level. No log file is created by default.

## Stop

Press **Ctrl+C** in the terminal running the collector. The scheduler shuts
down and waits for an in-progress scrape cycle to finish before exiting.

## Check

Watch the terminal output for each cycle's log messages. The `scrape_runs` table
records the status, number of saved products, and any error message for each
cycle. For the real collector, confirm that `DATABASE_URL` points to the shared
collector database before starting.

This is an initial runbook draft; update it after the team's live-site run.
