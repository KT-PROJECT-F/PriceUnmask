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
SCRAPE_TARGET_URLS=https://books.toscrape.com/
SCRAPE_INTERVAL_HOURS=0.25
```

To add a site, add its URL to `SCRAPE_TARGET_URLS`. Separate multiple URLs
with commas. Duplicate URLs are ignored in their first-seen order. If different
URLs list the same product, the collector saves only one price snapshot for
that product per run, using the first successfully saved result. The legacy
`SCRAPE_TARGET_URL` setting is used only when `SCRAPE_TARGET_URLS` is unset or
empty; do not set both. The site must have a supported scraper adapter. GitHub
Actions sets `SCRAPE_TARGET_URLS` and currently collects Books to Scrape only.
Keep other sites, including Web Scraper, out of the default list until their
use is approved; see #241 and [the shop evaluation](shop-evaluation.md).

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
Errors with at least one product saved produce status `partial`; errors with
no products saved produce status `failed`. This applies to both source
failures and database save failures. The API exposes the status, and the
dashboard displays `partial` as "Completed with partial results". Check the
target URL, network access, and database path to correct the problem. A
scrape failure does not stop the scheduler from attempting its next interval.

Each configured URL is attempted independently. If a listing page fails, its
URL and error are recorded in the scrape run's `error_message`, and the
collector continues with the remaining sources. Raw HTML snapshots fetched
before a failure are kept in `data/snapshots/`.

To verify failure handling against the test site, set
`SCRAPE_INTERVAL_HOURS=0.25` for this supervised drill. Stop the collector,
change `SCRAPE_TARGET_URLS` in `.env` to
`https://books.toscrape.com/nonexistent-page` (use only this URL for the
drill), and restart the collector. The immediate attempt should be recorded as
`failed`; leave the process running for at least 15 minutes and confirm another
run appears. Stop it with **Ctrl+C**, then restore
`SCRAPE_TARGET_URLS=https://books.toscrape.com/`,
and `SCRAPE_INTERVAL_HOURS=4` before restarting for routine operation.

## Live collector - Automated (Nov 2026 onwards - Issue #222)

**Previous setup (until 02 Nov 2026):**
- Owner: Saidivya (@Saidivya-20)
- Machine: "DESKTOP-MG4N0SP" (Windows 11), plugged in, sleep turned off, collector terminal left open
- Database: `data/priceunmask.db`, real data only, 8 Oct onwards
- Actual end: 02 Nov 2026 06:02 UTC (Run 60) - Extended INTENTIONALLY
- Gap honesty: 30 Oct PRESENT, 31 Oct GAP (demo day - ran on stale data from 30 Oct), 01 Nov GAP, 02 Nov RESUMED - ~70 hour gap per DB.
- Final totals till 02 Nov: 60 runs, 54 success, 6 failed, 60 products, 0 duplicates, 3240 snapshots
- Daily check: every working morning Saidivya ran `check_db` and posted on #155 (MANUAL - now retired)

**New setup (Issue #222 - Collector Reliability):**
- **Runs off personal laptop:** Collector now runs via GitHub Actions `.github/workflows/collector.yml` with cron `0 */4 * * *` (every 4 hours). No dependency on personal machine staying awake. This fixes outages 24-26 Oct and 30 Oct-02 Nov that spanned demo.
- **Automated health alerting:** `.github/workflows/health-check.yml` runs daily cron `0 1 * * *` and runs `python -m backend.devtools.check_db` automatically. It posts HEALTHY / CHECK REQUIRED to GitHub Actions summary. Manual morning comment on #155 is no longer needed.
- **Local dev still works:** For local testing, follow "Start" section: `python -m backend.scheduler.jobs` with `.env` configured.
- **Artifacts:** Each GitHub Actions run can upload DB as artifact if needed.

This satisfies #222 Acceptance Criteria: 1) Runs not on personal machine 2) Automated health check 3) Docs updated here.

## Get the newest data

The live database is restored from the GitHub Actions cache (see
collector.yml / health-check.yml), not exported from a laptop. To inspect it
locally, download the "priceunmask-db-*" cache from the most recent
successful run under Actions > Caches, or just run check_db as part of the
workflow and read the job summary.

## Demo database

The demo database is a local copy of a collector export with three synthetic
products added for dashboard demonstrations. The synthetic products have
made-up price histories and must not be presented as real market data.
The original export remains unchanged. Do not commit `.db` files.

### Build the demo database

1. Obtain the required collector export from Saidivya. Never copy the live
   collector database directly while it is running.

2. From the project root, copy the confirmed export to a separate demo file.
   Replace the source path only if the agreed export has a different name.

   ```powershell
   Copy-Item "$HOME\Downloads\priceunmask-20261028T045012Z.db" ".\data\priceunmask-demo-20261029.db"
   ```

3. Point `DATABASE_URL` at the demo copy for this PowerShell session:

   ```powershell
   $env:DATABASE_URL = "sqlite:///data/priceunmask-demo-20261029.db"
   ```
4. Check the database before seeding:

   ```powershell
   python -m backend.devtools.check_db
   ```

   Confirm the expected real products are present and that no products with
   `source="fake"` already exist.

5. Seed the synthetic products:

   ```powershell
   python -m backend.devtools.seed_fake_data
   ```

   The seeder refuses to run if fake products already exist. Do not run it
   twice against the same demo database.

6. Verify the result:

   ```powershell
   python -m backend.devtools.check_db
   python -c "import sqlite3; c = sqlite3.connect('data/priceunmask-demo-20261029.db'); print('Products by source:', c.execute('SELECT source, COUNT(*) FROM products GROUP BY source').fetchall()); print('Snapshots:', c.execute('SELECT COUNT(*) FROM price_snapshots').fetchone()[0]); print('Snapshot range:', c.execute('SELECT MIN(scraped_at), MAX(scraped_at) FROM price_snapshots').fetchone()); c.close()"
   ```

7. Start the app in the same terminal so it uses the demo database:

   ```powershell
   uvicorn backend.main:app --reload
   ```

   Open `http://127.0.0.1:8000/` and check a synthetic demo product,
   a real book, and the collector status. Do not trigger a new collection
   during the demo-data spot check.

8. When finished, stop the server with `Ctrl+C`. To restore the default
   database for subsequent commands in this terminal, run:

   ```powershell
   Remove-Item Env:DATABASE_URL
   ```

The database health check can report `CHECK REQUIRED` when the latest
collector run is older than 24 hours. Report this status honestly; adding
synthetic demo products does not make the collector data fresher.
