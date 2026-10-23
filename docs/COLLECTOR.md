# Collector runbook

The collector scrapes once immediately after startup, then repeats every
`SCRAPE_INTERVAL_HOURS` (4 hours by default). Each run fetches up to
`SCRAPE_MAX_PAGES` listing pages (3 by default), following the site's "next"
links. Runs and price snapshots are stored in the database configured by
`DATABASE_URL` (default: `data/priceunmask.db`). Settings, including `.env`,
are read at process startup; restart the collector after changing them.

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

- **At startup and before every scheduled cycle**, the collector marks every
  run that has been `running` for longer than `STALE_RUN_MINUTES` (default 30)
  as `failed`, and logs `Closed N stale scrape run(s)` (only when N > 0). If
  that clean-up fails, the error is logged and the collector carries on.
- **Before each cycle**, if another run is still `running` (for example a
  "Run now" from the dashboard), the cycle is skipped and the log shows
  `Scheduled scrape skipped; a run is already running`. One skip is normal.
  A stuck run is closed automatically at the next cycle once it is older than
  `STALE_RUN_MINUTES`; there is no need to restart the collector. If you see
  skips cycle after cycle, check the runs with
  `python -m backend.devtools.check_db`.
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

If any listing page fails during a multi-page run, the entire run is marked
`failed`, and no products from that run are saved. Raw HTML snapshots of pages
fetched before the failure are kept in `data/snapshots/` for diagnosis. This is
the honest result because a failed page means the collected catalogue may be
incomplete; saving only some products could make an incomplete run appear
successful. `partial` is different: every page was fetched, but some products
could not be saved to the database.

To verify failure handling against the test site, first set
`SCRAPE_INTERVAL_HOURS=0.25` for this supervised drill. Stop the collector,
change `SCRAPE_TARGET_URL` in `.env` to
`https://books.toscrape.com/nonexistent-page`, and restart it. The immediate
attempt should be recorded as `failed`; leave the process running for at least
15 minutes and confirm another run appears. Stop it with **Ctrl+C**, restore
`SCRAPE_TARGET_URL=https://books.toscrape.com/` and
`SCRAPE_INTERVAL_HOURS=4`, then restart for routine operation.

## Live collector (until 31 Oct)

- **Owner:** Saidivya (@Saidivya-20)
- **Machine:** `DESKTOP-MG4NO5P` (Windows 11), plugged in, sleep turned off,
  collector terminal left open
- **Database:** `data/collector.db`, real data only, no demo seed
- **Settings:** `SCRAPE_MAX_PAGES=3` (about 60 products per run),
  `SCRAPE_INTERVAL_HOURS=4`
- **Log file:** `data/collector.log`
- **Daily check:** every working morning Saidivya runs `check_db` on
  `data/collector.db` and posts one line on #155: date, health status, number
  of runs, last run time.

To get the newest data, ask Saidivya in the team chat. She runs, on the
collector machine:

```powershell
$env:DATABASE_URL = "sqlite:///data/collector.db"
python -m backend.devtools.export_db
```

and shares the file it prints, `data/exports/priceunmask-<UTC timestamp>.db`.
Do not copy `data/collector.db` directly while the collector is running.
