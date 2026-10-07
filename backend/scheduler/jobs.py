"""Scheduler and ingestion pipeline. Owner: Scheduler track.

Run the collector with:  python -m backend.scheduler.jobs
"""

import logging

from sqlalchemy.orm import Session

from backend.config import settings
from backend.db import crud
from backend.db.database import SessionLocal
from backend.scraper.product_scraper import scrape

SOURCE_KEY = "demo-shop"  # change when the target site is chosen
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
    saved = 0
    try:
        for item in scrape(settings.scrape_target_url):
            crud.upsert_product_and_snapshot(session, SOURCE_KEY, item, run)
            saved += 1
    except Exception as exc:
        logger.exception("Scrape cycle failed after saving %d products", saved)
        session.rollback()  # a failed database call leaves the session unusable until this
        status = "partial" if saved else "failed"
        crud.finish_scrape_run(session, run, status, saved, error=str(exc))
        return saved

    crud.finish_scrape_run(session, run, "success", saved)
    return saved


def build_scheduler():  # -> apscheduler BackgroundScheduler / BlockingScheduler
    """Interval job every settings.scrape_interval_hours, max_instances=1,
    coalesce=True, plus one run immediately at startup."""
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit("Scheduler not implemented yet. See docs/ARCHITECTURE.md")
