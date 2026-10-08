"""Scheduler and ingestion pipeline. Owner: Scheduler track.

Run the collector with:  python -m backend.scheduler.jobs
"""

import logging
from datetime import UTC, datetime

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
    Returns the number of products saved.
    """
    try:
        with SessionLocal() as session:
            return _run_cycle(session)
    except Exception:
        logger.exception("Scrape cycle could not run")
        return 0


def _run_cycle(session: Session) -> int:
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
    )
    return scheduler


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    init_db()
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
