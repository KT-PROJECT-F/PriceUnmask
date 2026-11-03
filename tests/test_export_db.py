import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from backend.db.database import Base, make_engine
from backend.db.models import PriceSnapshot, Product
from backend.devtools.export_db import export_db, main, sqlite_url_to_path


def count_rows(path: Path, table: str) -> int:
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute(f"select count(*) from {table}").fetchone()[0]


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

    engine.dispose()
    exported_engine.dispose()


def test_export_db_rejects_missing_source(tmp_path):
    source = tmp_path / "missing.db"

    with pytest.raises(FileNotFoundError, match="does not exist"):
        export_db(source, tmp_path / "exports")


def test_export_db_rejects_non_sqlite_file(tmp_path):
    source = tmp_path / "database.txt"
    source.write_text("not a database")

    with pytest.raises(ValueError, match="SQLite file"):
        export_db(source, tmp_path / "exports")


def test_sqlite_url_to_path_rejects_non_sqlite_url():
    with pytest.raises(ValueError, match="Unsupported database URL"):
        sqlite_url_to_path("postgresql://localhost/priceunmask")


def test_export_db_includes_rows_that_are_still_in_the_wal_file(tmp_path):
    source = tmp_path / "live.db"
    engine = make_engine(f"sqlite:///{source}")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            Product(
                source="demo",
                external_id="p1",
                name="P",
                url="https://example.com/p1",
            )
        )
        session.commit()

    exported = export_db(source, tmp_path / "exports")

    assert count_rows(exported, "products") == 1

    engine.dispose()


def test_export_db_removes_the_half_written_file_for_a_broken_database(tmp_path):
    source = tmp_path / "broken.db"
    source.write_text("this is not a database")
    exports = tmp_path / "exports"

    with pytest.raises(sqlite3.DatabaseError):
        export_db(source, exports)

    assert list(exports.glob("*.db")) == []


def test_export_db_does_not_overwrite_an_export_from_the_same_second(tmp_path, monkeypatch):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 10, 8, 12, 0, 0, tzinfo=UTC)

    monkeypatch.setattr("backend.devtools.export_db.datetime", FixedDatetime)

    source = tmp_path / "live.db"

    with closing(sqlite3.connect(source)) as connection:
        connection.execute("create table t (x)")
        connection.commit()

    export_db(source, tmp_path / "exports")

    with pytest.raises(FileExistsError, match="already exists"):
        export_db(source, tmp_path / "exports")


def test_main_exits_with_a_clear_message_when_the_database_is_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "backend.config.settings",
        SimpleNamespace(database_url="sqlite:///missing.db"),
    )

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code
    assert "does not exist" in str(excinfo.value)


def test_main_exits_with_a_clear_message_for_a_broken_database(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "broken.db").write_text("this is not a database")

    monkeypatch.setattr(
        "backend.config.settings",
        SimpleNamespace(database_url="sqlite:///broken.db"),
    )

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert "Database export failed" in str(excinfo.value)
