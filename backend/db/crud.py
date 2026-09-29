"""Data-access functions. Owner: DB track.

Rule: no other module writes raw SQLAlchemy queries. Scheduler, API and analysis
call these functions. That keeps the schema changeable in one place.
Signatures below are the contract; bodies are the DB owner's first task.
"""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy.orm import Session

from backend.db.models import PriceSnapshot, Product, ScrapeRun
from backend.scraper.product_scraper import ScrapedProduct


def start_scrape_run(session: Session) -> ScrapeRun:
    """Insert a ScrapeRun with status 'running' and return it."""
    raise NotImplementedError


def finish_scrape_run(
    session: Session, run: ScrapeRun, status: str, products_seen: int, error: str | None = None
) -> None:
    """Set finished_at, status, products_seen, error_message."""
    raise NotImplementedError


def upsert_product_and_snapshot(
    session: Session, source: str, item: ScrapedProduct, run: ScrapeRun
) -> PriceSnapshot:
    """Find-or-create the Product (by source + external_id), update name/url/last_seen_at,
    then append one PriceSnapshot. Never updates an existing snapshot."""
    raise NotImplementedError


def list_products(session: Session, search: str | None = None) -> Sequence[Product]:
    """All active products, optionally filtered by case-insensitive name search."""
    raise NotImplementedError


def get_product(session: Session, product_id: int) -> Product | None:
    raise NotImplementedError


def get_history(
    session: Session, product_id: int, since: datetime | None = None
) -> Sequence[PriceSnapshot]:
    """Snapshots for one product, oldest first."""
    raise NotImplementedError


def list_scrape_runs(session: Session, limit: int = 20) -> Sequence[ScrapeRun]:
    """Most recent runs first."""
    raise NotImplementedError
