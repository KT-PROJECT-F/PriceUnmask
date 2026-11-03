
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Event

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session, sessionmaker

from backend.db.database import Base, get_session, make_engine
from backend.db.models import PriceSnapshot
from backend.scheduler import jobs
from backend.scraper.product_scraper import ScrapedProduct


def test_api_can_read_while_collector_write_is_uncommitted(
    tmp_path,
    monkeypatch,
):
    """The API sees committed data while the collector has an open write."""
    from backend.main import app

    db_path = tmp_path / "concurrency.db"
    engine = make_engine(f"sqlite:///{db_path.as_posix()}")
    Base.metadata.create_all(engine)

    class CollectorSession(Session):
        pass

    CollectorSessionLocal = sessionmaker(
        bind=engine,
        class_=CollectorSession,
        autoflush=False,
        expire_on_commit=False,
    )
    ApiSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    writer_paused = Event()
    allow_commit = Event()

    def pause_before_snapshot_commit(session, _flush_context):
        if any(isinstance(obj, PriceSnapshot) for obj in session.new):
            writer_paused.set()
            if not allow_commit.wait(timeout=10):
                raise TimeoutError("Test did not release the collector writer.")

    event.listen(CollectorSession, "after_flush", pause_before_snapshot_commit)

    monkeypatch.setattr(jobs, "SessionLocal", CollectorSessionLocal)
    monkeypatch.setattr(
        jobs,
        "scrape",
        lambda _url: [
            ScrapedProduct(
                external_id="concurrency-test-1",
                name="Concurrency Test Book",
                url="https://example.com/concurrency-test",
                current_price_minor=129900,
                original_price_minor=None,
                in_stock=True,
                currency="INR",
                scraped_at=datetime.now(UTC),
            )
        ],
    )

    # The test database is already initialized.
    monkeypatch.setattr("backend.main.init_db", lambda: None)

    def override_get_session():
        with ApiSessionLocal() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    try:
        with TestClient(app) as client:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(jobs.run_scrape_cycle)

                try:
                    assert writer_paused.wait(timeout=5), (
                        "Collector did not reach the uncommitted snapshot write."
                    )

                    # The collector has flushed its rows but has not committed.
                    response = client.get("/api/products")
                    assert response.status_code == 200
                    assert response.json() == []

                finally:
                    # Always release the writer, including when an assertion fails.
                    allow_commit.set()

                assert future.result(timeout=10) == 1

            # Each API request gets a fresh session.
            response = client.get("/api/products")
            assert response.status_code == 200

            products = response.json()
            assert len(products) == 1
            assert products[0]["name"] == "Concurrency Test Book"

    finally:
        allow_commit.set()
        app.dependency_overrides.pop(get_session, None)
        event.remove(
            CollectorSession,
            "after_flush",
            pause_before_snapshot_commit,
        )
        engine.dispose()
