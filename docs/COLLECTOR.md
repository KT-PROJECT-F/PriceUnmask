# Collector runbook

The collector scrapes once immediately after startup, then repeats every
`SCRAPE_INTERVAL_HOURS` (4 hours by default). Runs and price snapshots are
stored in the database configured by `DATABASE_URL` (default:
`data/priceunmask.db`). Settings, including `.env`, are read at process startup;
restart the collector after changing them.

## Start

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Set the target and interval in `.env` before starting. For a supervised
integration check only, use a 15-minute interval to observe multiple cycles;
restore the 4-hour interval afterward. Never commit `.env`.

```dotenv
SCRAPE_TARGET_URL=https://books.toscrape.com/
SCRAPE_INTERVAL_HOURS=0.25
```

Start the process and leave its terminal open:

```powershell
python -m backend.scheduler.jobs
```

The first cycle starts immediately. The next cycle starts at the configured
interval. Keep requests polite; do not use a short test interval in routine
operation.

## Check that it is alive

In the collector terminal, look for timestamped log messages for scrape cycles.
From another PowerShell window, check for the process:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*backend.scheduler.jobs*' } | Select-Object ProcessId, CommandLine
```

Each cycle, including failures, should create a row in `scrape_runs`. With the
default database, inspect the 10 newest runs using Python's built-in SQLite
module:

```powershell
python -c "import sqlite3; c=sqlite3.connect('data/priceunmask.db'); print(*c.execute('SELECT id, started_at, finished_at, status, products_seen, error_message FROM scrape_runs ORDER BY started_at DESC LIMIT 10'), sep='\n'); c.close()"
```

For another `DATABASE_URL`, inspect its SQLite file instead. Alternatively,
open the configured database in DB Browser for SQLite and view the
`scrape_runs` table. If the API is running against the same database, the runs
are also available at `http://127.0.0.1:8000/api/scrape-runs`.

## Logs and snapshots

Logs are written to the collector's terminal; the collector does not create a
log file by default. Raw fetched HTML snapshots are saved under
`data/snapshots/` as timestamped `.html` files. Product rows, price snapshots,
and run history are stored in the configured database.

## Stop

Press **Ctrl+C** in the collector terminal. The scheduler waits for an active
cycle to finish before exiting.

## When a run fails

Check the terminal traceback and the run's `error_message` in `scrape_runs`.
For a failed run, `status` is `failed`; an incomplete set of saved products is
marked `partial`. Check the target URL, network access, and database path, then
correct the problem. A scrape failure is recorded and does not stop the
scheduler from attempting its next interval.

To verify failure handling against the test site, first set
`SCRAPE_INTERVAL_HOURS=0.25` for this supervised drill. Stop the collector,
change `SCRAPE_TARGET_URL` in `.env` to
`https://books.toscrape.com/nonexistent-page`, and restart it. The immediate
attempt should be recorded as `failed`; leave the process running for at least
15 minutes and confirm another run appears. Stop it with **Ctrl+C**, restore
`SCRAPE_TARGET_URL=https://books.toscrape.com/` and
`SCRAPE_INTERVAL_HOURS=4`, then restart for routine operation.
