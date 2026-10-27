# Scheduler Design

## 1. Overview
Scheduler runs `run_scrape_cycle()` immediately at startup and then every `scrape_interval_hours` (default 4h). Uses APScheduler BlockingScheduler with `coalesce=True`.

## 2. Stale Run Handling
At start of each cycle and at main() startup:
`crud.mark_stale_runs_failed(older_than=timedelta(minutes=settings.stale_run_minutes))`
If DB locked during cleanup, exception is logged, rollback, cycle continues - never crashes.

## 3. Overlap Prevention
`crud.has_running_scrape_run()` - if true, log warning "Scheduled scrape skipped; a run is already running" and return 0. Ensures only one run at a time.

## 4. Error Handling - Never Raise
`run_scrape_cycle()` and `_run_cycle()` never raise. Scrape failure -> finish run as "failed". Upsert failure per item -> rollback that item, collect error, continue. No errors -> "success", some saved + errors -> "partial", zero saved -> "failed".

## 5. API Triggered Runs
`run_scrape_cycle_for_run(run_id)` processes an existing run created by API. If run not found or not "running", log and skip.