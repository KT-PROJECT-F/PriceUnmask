"""Scheduler and ingestion pipeline. Owner: Scheduler track.

Run the collector with:  python -m backend.scheduler.jobs
"""

from backend.db.database import SessionLocal  # noqa: F401  (used once implemented)

SOURCE_KEY = "demo-shop"  # change when the target site is chosen


def run_scrape_cycle() -> int:
    """One full cycle: start_scrape_run -> scrape() -> upsert each item -> finish_scrape_run.

    Must NEVER raise out of this function: catch errors, record status 'failed' or
    'partial' with the error message, log it, and return. An exception that kills the
    scheduler thread means history silently stops growing.
    Returns the number of products saved.
    """
    raise NotImplementedError


def build_scheduler():  # -> apscheduler BackgroundScheduler / BlockingScheduler
    """Interval job every settings.scrape_interval_hours, max_instances=1,
    coalesce=True, plus one run immediately at startup."""
    raise NotImplementedError


if __name__ == "__main__":
    raise SystemExit("Scheduler not implemented yet. See docs/ARCHITECTURE.md")
