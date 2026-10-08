"""Data-access functions. Owner: DB track.

Rule: no other module writes raw SQLAlchemy queries. Scheduler, API and analysis
call these functions. That keeps the schema changeable in one place.
Signatures below are the contract; bodies are the DB owner's first task.

Commit policy: the write functions (start_scrape_run, finish_scrape_run,
upsert_product_and_snapshot) commit themselves. Callers must not commit again.
Read functions never commit.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.db.models import PriceSnapshot, Product, ScrapeRun
from backend.scraper.product_scraper import ScrapedProduct


def start_scrape_run(session: Session) -> ScrapeRun:
    run = ScrapeRun(
        status="running",
        products_seen=0,
    )

    session.add(run)
    session.commit()
    session.refresh(run)

    return run


def finish_scrape_run(
    session: Session,
    run: ScrapeRun,
    status: str,
    products_seen: int,
    error: str | None = None,
) -> None:
    """Set finished_at, status, products_seen, error_message."""
    run.finished_at = datetime.now(UTC)
    run.status = status
    run.products_seen = products_seen
    run.error_message = error
    session.commit()


def upsert_product_and_snapshot(
    session: Session,
    source: str,
    item: ScrapedProduct,
    run: ScrapeRun,
) -> PriceSnapshot:
    """Find-or-create the Product (by source + external_id), update name/url/last_seen_at,
    then append one PriceSnapshot. Never updates an existing snapshot."""

    statement = select(Product).where(
        Product.source == source,
        Product.external_id == item.external_id,
    )

    product = session.scalar(statement)

    if product is None:
        product = Product(
            source=source,
            external_id=item.external_id,
            name=item.name,
            url=item.url,
            currency=item.currency,
            is_active=True,
            last_seen_at=item.scraped_at,
        )
        session.add(product)
        session.flush()
    else:
        product.name = item.name
        product.url = item.url

    # A product seen again by the scraper is considered active.
    product.is_active = True

    product.last_seen_at = item.scraped_at
    snapshot = PriceSnapshot(
        product_id=product.id,
        scrape_run_id=run.id,
        scraped_at=item.scraped_at,
        current_price_minor=item.current_price_minor,
        original_price_minor=item.original_price_minor,
        in_stock=item.in_stock,
    )

    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)

    return snapshot


def list_products(
    session: Session,
    search: str | None = None,
) -> Sequence[Product]:
    """Return active products, optionally filtered by name."""

    statement = select(Product).where(Product.is_active.is_(True))

    if search:
        statement = statement.where(Product.name.ilike(f"%{search}%"))

    statement = statement.order_by(Product.name)

    return session.scalars(statement).all()


def get_product(
    session: Session,
    product_id: int,
) -> Product | None:
    """Return one product by id, or None if it does not exist."""

    return session.get(Product, product_id)


def get_history(
    session: Session,
    product_id: int,
    since: datetime | None = None,
) -> Sequence[PriceSnapshot]:
    """Return product price history oldest first."""

    statement = (
        select(PriceSnapshot)
        .where(PriceSnapshot.product_id == product_id)
        .order_by(PriceSnapshot.scraped_at.asc())
    )

    if since is not None:
        if since.tzinfo is None or since.utcoffset() is None:
            raise ValueError("since must be a timezone-aware datetime")

        since = since.astimezone(UTC)
        statement = statement.where(PriceSnapshot.scraped_at >= since)
    return session.scalars(statement).all()


def list_scrape_runs(
    session: Session,
    limit: int = 20,
) -> Sequence[ScrapeRun]:
    """Return most recent scrape runs first."""

    statement = select(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(limit)

    return session.scalars(statement).all()


def count_runs_by_status(session: Session) -> dict[str, int]:
    """Return the number of scrape runs for each status."""
    rows = session.execute(
        select(ScrapeRun.status, func.count(ScrapeRun.id)).group_by(ScrapeRun.status)
    ).all()

    return {status: count for status, count in rows}


def count_products(session: Session) -> int:
    """Return the total number of products, including inactive products."""
    return session.scalar(select(func.count()).select_from(Product)) or 0


def count_snapshots_by_run(session: Session) -> dict[int, int]:
    """Return snapshot counts for runs that have snapshots."""
    rows = session.execute(
        select(
            PriceSnapshot.scrape_run_id,
            func.count(PriceSnapshot.id),
        )
        .where(PriceSnapshot.scrape_run_id.is_not(None))
        .group_by(PriceSnapshot.scrape_run_id)
    ).all()

    return {run_id: count for run_id, count in rows}


def list_products_not_seen_in_run(
    session: Session,
    run_id: int,
) -> Sequence[Product]:
    """Return products without a snapshot associated with the given run."""
    seen_product_ids = select(PriceSnapshot.product_id).where(PriceSnapshot.scrape_run_id == run_id)

    statement = select(Product).where(~Product.id.in_(seen_product_ids)).order_by(Product.name)

    return session.scalars(statement).all()
