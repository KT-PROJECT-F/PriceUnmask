from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from backend.db.database import Base
from backend.db.models import PriceSnapshot, Product
from backend.devtools.export_db import export_db, sqlite_url_to_path


def test_sqlite_url_to_path():
    assert sqlite_url_to_path("sqlite:///data/priceunmask.db") == Path("data/priceunmask.db")


def test_export_db_preserves_product_and_snapshot_counts(tmp_path):
    source = tmp_path / "source.db"
    export_folder = tmp_path / "exports"

    engine = create_engine(f"sqlite:///{source}")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        product = Product(
            source="demo-shop",
            external_id="product-1",
            name="Test Product",
            url="https://example.com/product-1",
            currency="INR",
            is_active=True,
            created_at=datetime.now(UTC),
            last_seen_at=datetime.now(UTC),
        )
        session.add(product)
        session.flush()

        snapshot = PriceSnapshot(
            product_id=product.id,
            scraped_at=datetime.now(UTC),
            current_price_minor=129900,
            original_price_minor=149900,
            in_stock=True,
        )
        session.add(snapshot)
        session.commit()

        product_count = session.scalar(select(func.count()).select_from(Product))
        snapshot_count = session.scalar(select(func.count()).select_from(PriceSnapshot))

    exported = export_db(source, export_folder)

    assert exported.exists()
    assert exported.parent == export_folder

    exported_engine = create_engine(f"sqlite:///{exported}")

    with Session(exported_engine) as session:
        exported_product_count = session.scalar(select(func.count()).select_from(Product))
        exported_snapshot_count = session.scalar(select(func.count()).select_from(PriceSnapshot))

    assert exported_product_count == product_count
    assert exported_snapshot_count == snapshot_count


def test_export_db_rejects_missing_source(tmp_path):
    source = tmp_path / "missing.db"

    with pytest.raises(FileNotFoundError, match="does not exist"):
        export_db(source, tmp_path / "exports")


def test_export_db_rejects_non_sqlite_file(tmp_path):
    source = tmp_path / "database.txt"
    source.write_text("not a database")

    with pytest.raises(ValueError, match="SQLite .db file"):
        export_db(source, tmp_path / "exports")


def test_sqlite_url_to_path_rejects_non_sqlite_url():
    with pytest.raises(ValueError, match="Unsupported database URL"):
        sqlite_url_to_path("postgresql://localhost/priceunmask")
