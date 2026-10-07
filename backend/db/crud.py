"""Data-access functions. Owner: DB track.

Rule: no other module writes raw SQLAlchemy queries. Scheduler, API and analysis
call these functions. That keeps the schema changeable in one place.
Signatures below are the contract; bodies are the DB owner's first task.

Write functions commit their own changes. Callers should not rely on an additional
commit after calling these functions.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
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
    *,
    status: str,
    products_seen: int,
    error_message: str | None = None,
) -> ScrapeRun:
    run.finished_at = datetime.now(UTC)
    run.status = status
    run.products_seen = products_seen
    run.error_message = error_message

    session.commit()
    session.refresh(run)

    return run


def upsert_product_and_snapshot(
    session: Session,
    source: str,
    item: ScrapedProduct,
    run: ScrapeRun,
) -> PriceSnapshot:
    """Create or update a product and append a new price snapshot.

    Never updates an existing snapshot.
    """
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
        statement = statement.where(PriceSnapshot.scraped_at >= since)

    return session.scalars(statement).all()


def list_scrape_runs(
    session: Session,
    limit: int = 20,
) -> Sequence[ScrapeRun]:
    """Return most recent scrape runs first."""

    statement = select(ScrapeRun).order_by(ScrapeRun.started_at.desc()).limit(limit)

    return session.scalars(statement).all()
