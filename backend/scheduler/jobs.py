"""Scheduler and ingestion pipeline. Owner: Scheduler track.

Run the collector with:  python -m backend.scheduler.jobs
"""

import logging
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db import crud
from backend.db.database import SessionLocal, init_db
from backend.db.models import ScrapeRun
from backend.scraper.product_scraper import scrape

SOURCE_KEY = "books-toscrape"
logger = logging.getLogger(__name__)


def run_scrape_cycle() -> int:
    """One full cycle: start_scrape_run -> scrape() -> upsert each item -> finish_scrape_run.

    Must NEVER raise out of this function: catch errors, record status 'failed' or
    'partial' with the error message, log it, and return. An exception that kills the
    scheduler thread means history silently stops growing.

    Before the overlap check, runs that have been 'running' for longer than
    settings.stale_run_minutes are marked failed. If that clean-up fails (for
    example, the database is locked), the error is logged, the session is rolled
    back, and the cycle carries on: a fresh 'running' run still makes it skip.
    Returns the number of products saved.
    """
    try:
        with SessionLocal() as session:
            try:
                stale_count = crud.mark_stale_runs_failed(
                    session,
                    older_than=timedelta(minutes=settings.stale_run_minutes),
                )
                if stale_count:
                    logger.info("Closed %s stale scrape run(s)", stale_count)
            except Exception:
                logger.exception("Could not close stale runs before scheduled cycle")
                session.rollback()

            if crud.has_running_scrape_run(session):
                logger.warning("Scheduled scrape skipped; a run is already running")
                return 0
            return _run_cycle(session)
    except Exception:
        logger.exception("Scrape cycle could not run")
        return 0


def run_scrape_cycle_for_run(run_id: int) -> int:
    """Process an existing scrape run created by the API."""
    try:
        with SessionLocal() as session:
            run = crud.get_scrape_run(session, run_id)

            if run is None:
                logger.error("Scrape run %s was not found", run_id)
                return 0

            if run.status != "running":
                logger.warning(
                    "Scrape run %s is not running; skipping it",
                    run_id,
                )
                return 0

            return _run_cycle(session, run)
    except Exception:
        logger.exception("Scrape run %s could not be processed", run_id)
        return 0


def _run_cycle(
    session: Session,
    run: ScrapeRun | None = None,
) -> int:
    if run is None:
        run = crud.start_scrape_run(session)

    run_id = run.id
    try:
        items = scrape(settings.scrape_target_url)
    except Exception as exc:
        logger.exception("Scraping failed for run %s", run_id)
        _finish_run(session, run, run_id, "failed", 0, str(exc))
        return 0

    saved = 0
    errors: list[str] = []
    if not items:
        logger.warning("Scrape returned no products for run %s", run_id)

    for item in items:
        try:
            crud.upsert_product_and_snapshot(session, SOURCE_KEY, item, run)
        except Exception as exc:
            external_id = item.external_id
            logger.exception("Could not save scraped item %s for run %s", external_id, run_id)
            errors.append(f"{external_id}: {exc}")
            try:
                session.rollback()
            except Exception as rollback_exc:
                logger.exception("Could not roll back after saving item for run %s", run_id)
                errors.append(f"Rollback failed: {rollback_exc}")
                break
        else:
            saved += 1

    if not errors:
        status = "success"
    elif saved:
        status = "partial"
    else:
        status = "failed"

    _finish_run(
        session,
        run,
        run_id,
        status,
        saved,
        "; ".join(errors) if errors else None,
    )
    return saved


def _finish_run(
    session: Session,
    run: ScrapeRun,
    run_id: int,
    status: str,
    saved: int,
    error: str | None,
) -> None:
    try:
        crud.finish_scrape_run(session, run, status, saved, error=error)
    except Exception as exc:
        logger.exception("Could not finish scrape run %s", run_id)
        try:
            session.rollback()
        except Exception:
            logger.exception("Could not roll back after finishing scrape run %s", run_id)

        failure = f"{error}; finishing the run also failed: {exc}" if error else str(exc)
        try:
            crud.finish_scrape_run(session, run, "failed", saved, error=failure)
        except Exception:
            logger.exception("Could not record failure for scrape run %s", run_id)


def build_scheduler() -> BlockingScheduler:
    """Interval job every settings.scrape_interval_hours, max_instances=1,
    coalesce=True, plus one run immediately at startup."""
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_scrape_cycle,
        trigger="interval",
        hours=settings.scrape_interval_hours,
        next_run_time=datetime.now(UTC),
        max_instances=1,
        coalesce=True,
        misfire_grace_time=None,
    )
    return scheduler


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    init_db()
    try:
        with SessionLocal() as session:
            stale_count = crud.mark_stale_runs_failed(
                session,
                older_than=timedelta(minutes=settings.stale_run_minutes),
            )
        logger.info("Closed %s stale scrape run(s)", stale_count)
    except Exception:
        logger.exception("Could not close stale scrape runs at startup")

    scheduler = build_scheduler()
    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Collector stopped by user")
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=True)


if __name__ == "__main__":
    main()
