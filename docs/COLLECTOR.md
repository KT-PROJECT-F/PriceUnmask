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
- **Database:** `data/priceunmask.db`, real data only, no demo seed. Contains real books since 8 oct (single-page runs at first, 3-page runs since 16 oct), with a gap on 24 to 26 oct (weekend laptop off). Gap is mentioned so demo builder knows data is not continuous.
- **Settings:** `SCRAPE_MAX_PAGES=3` (about 60 products per run),
  `SCRAPE_INTERVAL_HOURS=4`
- **Log file:** `data/collector.log`
- **Daily check:** every working morning Saidivya runs `check_db` on
  `data/priceunmask.db` and posts one line on #155: date, health status, number
  of runs, last run time.

To get the newest data, ask Saidivya in the team chat. She runs, on the
collector machine:

```powershell
$env:DATABASE_URL = "sqlite:///data/priceunmask.db"
python -m backend.devtools.export_db
```

and shares the file it prints, `data/exports/priceunmask-<UTC timestamp>.db`.
Do not copy `data/priceunmask.db` directly while the collector is running.

## Get the newest data

1. Ask Saidivya for a fresh export (see "Live collector" above for the
   command she runs). Never copy `data/priceunmask.db` itself.
2. Put the file in `data/exports/` in your own clone and keep its name:
   `priceunmask-<UTC timestamp>.db`, no spaces, the date is in the name.
   `.db` files are never committed.
3. Check it with `check_db`. Point `DATABASE_URL` at the file for this
   terminal only:

   ```powershell
   $env:DATABASE_URL = "sqlite:///data/exports/priceunmask-<UTC timestamp>.db"
   python -m backend.devtools.check_db
   ```

4. Check which dates it really covers, and how many snapshots it has:

   ```powershell
   python -c "import sqlite3; c = sqlite3.connect('data/exports/priceunmask-<UTC timestamp>.db'); print(c.execute('SELECT MIN(scraped_at), MAX(scraped_at), COUNT(*) FROM price_snapshots').fetchone())"
   ```

   The newest `scraped_at` should be close to the "Finished at" of the
   latest run in `check_db`. If it is much older, you have the wrong file.

5. When you are done, close the terminal or run
   `Remove-Item Env:DATABASE_URL`, so the app uses its normal database again.


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
   $env:DATABASE_URL = "sqlite:///C:/Users/venky/OneDrive/Desktop/PriceUnmask-recovery/data/priceunmask-demo-20261029.db"
   ```

   Use your own absolute project path if it differs.

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

## Demo database

The demo database is a local copy of a collector export with three synthetic products added for dashboard demonstrations. The synthetic products have made-up price histories and must not be presented as real market data. The original export remains unchanged. Do not commit `.db` files.

1. **Get the export.** Download the collector export announced by Saidivya in the latest comment on issue #198. Use that exact export file.

2. **Copy the export.** From the project root, copy the downloaded export to a separate demo database file. Replace the example date with the date you are building the demo database.

   ```powershell
   Copy-Item "$HOME\Downloads\<actual-export-filename>.db" ".\data\priceunmask-demo-<YYYYMMDD>.db"
   ```

3. **Select the demo copy.** From the project root, set `DATABASE_URL` for this PowerShell session. Use the same date as the copied file.

   ```powershell
   $env:DATABASE_URL = "sqlite:///data/priceunmask-demo-<YYYYMMDD>.db"
   ```

4. **Check the database before seeding.** Confirm the database contains the expected real products and no products with `source="fake"`. Do not seed the original export.

5. **Seed the synthetic demo products.** Run:

   ```powershell
   python -m backend.devtools.seed_fake_data
   ```

   The seeder adds three synthetic products with made-up price histories. It refuses to seed a database that already contains fake-source products.

6. **Verify the demo copy.** Check product and snapshot counts, then run the database health check against the demo file:

   ```powershell
   python -m backend.devtools.check_db --db data/priceunmask-demo-<YYYYMMDD>.db
   ```

   Record the actual health status and any warnings. A `CHECK REQUIRED` result must be reported with its reason; do not describe the database as healthy unless the check confirms it.

7. **Keep the export safe.** Do not modify the original export or commit any `.db` files. Treat synthetic product prices and trust scores as demonstration data, not real market data.