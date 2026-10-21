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

Each cycle, including failures, creates a row in `scrape_runs`. To see the runs,
snapshot counts and the health status:

```powershell
python -m backend.devtools.check_db
```

For another database, set `DATABASE_URL` for that terminal first, for example
`$env:DATABASE_URL = "sqlite:///data/exports/priceunmask-<timestamp>.db"`.

### Stale and overlapping runs

- **At startup**, the collector marks every run that has been `running` for
  longer than `STALE_RUN_MINUTES` (default 30) as `failed`, and logs
  `Closed N stale scrape run(s)`. If that clean-up fails, the error is logged
  and the collector still starts.
- **Before each cycle**, if another run is still `running` (for example a
  "Run now" from the dashboard), the cycle is skipped and the log shows
  `Scheduled scrape skipped; a run is already running`. One skip is normal.
  If you see it cycle after cycle, a run is stuck: check it with
  `python -m backend.devtools.check_db`, then restart the collector so the
  startup clean-up closes it.
## Logs and snapshots

By default, logs go only to the terminal. For a long or unattended run, write
them to a file:

```powershell
python -m backend.scheduler.jobs *> data/collector.log
```

Use `*>>` instead of `*>` to append to an existing log. Raw HTML of each fetched
page is saved in `data/snapshots/`. Products, price snapshots and runs are in
the database set by `DATABASE_URL`.

## If the laptop sleeps

Nothing runs while the laptop sleeps or is off. After it wakes, the scheduler
runs one missed cycle (not one per missed interval), then continues on its
interval. In `scrape_runs` this shows as a gap between two `started_at` times.
For a long run: plug in the laptop and turn sleep off.

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
