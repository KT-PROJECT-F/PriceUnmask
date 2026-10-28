# Scheduler Design

## What it does
The scheduler runs a scrape cycle immediately at startup and then every `scrape_interval_hours`. Each cycle writes a row in `scrape_runs` and saves products/snapshots. It is started with `python -m backend.scheduler.jobs`.

## Decisions
1. **Job must never raise** - `run_scrape_cycle()` catches all exceptions and marks run as `failed`/`partial` instead of raising. Chose this because scheduler thread must stay alive. See `backend/scheduler/jobs.py:22` and `backend/scheduler/jobs.py:99`. Did not choose to let it crash.
2. **Stale runs closed before every cycle** - At start of cycle we call `crud.mark_stale_runs_failed(older_than=STALE_RUN_MINUTES)` - `backend/scheduler/jobs.py:36`. Why: laptop sleep leaves `running` forever. If DB locked, log and continue, not crash.
3. **Skip if already running** - `crud.has_running_scrape_run()` check - `backend/scheduler/jobs.py:45`. If true, log "Scheduled scrape skipped" and return. Chose single-run guarantee over overlapping runs. Did not choose lock file.
4. **Every cycle writes a scrape_runs row** - `_run_cycle` starts a run via `start_scrape_run()` - `backend/scheduler/jobs.py:88`. Why: observability for #155 morning line and gap detection.

## How it fails, and what happens then
- Scrape throws: run marked `failed` via `_finish_run`.
- Upsert of one product fails: rollback that product, add to errors list, continue others. At end, if some saved + errors -> `partial`, if zero saved -> `failed`.
- DB locked on stale cleanup: exception logged, session rollback, cycle continues.
- Laptop sleeps mid-run: run stays `running`, next cycle marks it `failed` after `STALE_RUN_MINUTES`.

## How it is tested
Unit tests mock `scrape` and `SessionLocal`, check `mark_stale_runs_failed` called, `has_running_scrape_run` skip logic, and `run_scrape_cycle()` never raises. Manual test: run `python -m backend.scheduler.jobs` for one interval, check `data/priceunmask.db` has new `scrape_runs`. `pytest -q`, `ruff check .`, `ruff format --check .` pass.

## Known limits and what we would do next
Weekend gap on 24-26 Oct happened because live collector runs only on Saidivya's laptop, which was off. No cloud VM or watchdog. Next: run collector on always-on machine or add health check that alerts if no run in 6h.

### Collector Stop Plan - Issue #198
- Collector running till 31 Oct 6 PM, after final check DB archived for demo. Final export priceunmask-20261028T045012Z.db - OLDEST 2026-10-08, NEWEST 2026-10-28 04:44, 1160 snapshots, HEALTHY.