"""ORM models. This file IS the data contract; change it only via a PR the mentor approves.

Money rule: prices are stored as INTEGER minor units (paise / cents), never floats.
  Rs 1,299.50  ->  129950
Floats cannot represent most decimals exactly, and a "was 1299.4999999" bug in a
price-comparison app is the kind of thing users screenshot.

Time rule: every timestamp is timezone-aware UTC. SQLite has no timezone type, so every
datetime column uses UTCDateTime below: it stores naive UTC and always returns aware UTC.
Saving a naive datetime raises, because we cannot know which timezone it meant.
"""

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator[datetime]):
    """Stores naive UTC in the database, returns timezone-aware UTC in Python."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError(f"naive datetime {value!r}: use a timezone-aware UTC datetime")
        return value.astimezone(UTC).replace(tzinfo=None)

    def process_result_value(self, value: datetime | None, dialect: Dialect) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class Product(Base):
    """One real product on one site. Created the first time the scraper sees it."""

    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_product_source_ext"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(50))  # site key, e.g. "demo-shop"
    external_id: Mapped[str] = mapped_column(String(200))  # stable id on that site (SKU/slug)
    name: Mapped[str] = mapped_column(String(500))
    url: Mapped[str] = mapped_column(String(1000))
    currency: Mapped[str] = mapped_column(String(3), default="INR")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    snapshots: Mapped[list["PriceSnapshot"]] = relationship(
        back_populates="product", order_by="PriceSnapshot.scraped_at"
    )


class ScrapeRun(Base):
    """One execution of the scrape job. Lets us prove the system ran unattended,
    and see exactly when and why it failed."""

    __tablename__ = "scrape_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    status: Mapped[str] = mapped_column(String(20), default="running")
    # status is one of: running, success, partial, failed
    products_seen: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)


class PriceSnapshot(Base):
    """One observed price for one product at one moment. Append-only: never UPDATE these."""

    __tablename__ = "price_snapshots"
    __table_args__ = (Index("ix_snapshot_product_time", "product_id", "scraped_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    scrape_run_id: Mapped[int | None] = mapped_column(ForeignKey("scrape_runs.id"))
    scraped_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    current_price_minor: Mapped[int] = mapped_column(Integer)
    original_price_minor: Mapped[int | None] = mapped_column(Integer)  # strikethrough, if shown
    in_stock: Mapped[bool | None] = mapped_column(Boolean)

    product: Mapped[Product] = relationship(back_populates="snapshots")
