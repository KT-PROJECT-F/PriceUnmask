"""Scheduler and ingestion pipeline. Owner: Scheduler track.

Run the collector with:  python -m backend.scheduler.jobs
"""

from backend.config import settings
from backend.db import crud
from backend.db.database import SessionLocal  # noqa: F401  (used once implemented)
from backend.scraper.product_scraper import scrape

SOURCE_KEY = "demo-shop"  # change when the target site is chosen


def run_scrape_cycle() -> int:
    """One full cycle: start_scrape_run -> scrape() -> upsert each item -> finish as success.

    Must NEVER raise out of this function: catch errors, record status 'failed' or
    'partial' with the error message, log it, and return. An exception that kills the
    scheduler thread means history silently stops growing.
    Returns the number of products saved.
    """
    with SessionLocal() as session:
        run = crud.start_scrape_run(session)
        try:
            products = scrape(settings.scrape_target_url, source=SOURCE_KEY)
            count = 0
            for prod in products:
                crud.upsert_product_and_snapshot(session, prod)
                count += 1
            crud.finish_scrape_run(session, run, status="success", products_seen=count)
            return count
        except Exception as e:
            crud.finish_scrape_run(session, run, status="failed", products_seen=0, error=str(e))
            return 0


def build_scheduler():  # -> apscheduler BackgroundScheduler / BlockingScheduler
    """Interval job every settings.scrape_interval_hours, max_instances=1,
    coalesce=True, plus one run immediately at startup."""
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit("Scheduler not implemented yet. See docs/ARCHITECTURE.md")
