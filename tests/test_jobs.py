from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from backend.db.crud import list_products, list_scrape_runs
from backend.db.database import Base, make_engine
from backend.db.models import PriceSnapshot
from backend.scheduler import jobs
from backend.scraper.product_scraper import ScrapedProduct


class FakeSession:
    def __init__(self):
        self.rollbacks = 0

    def __enter__(self):
        return self

    def rollback(self):
        self.rollbacks += 1

    def __exit__(self, *a):
        return False


def make_item(ext_id):
    return ScrapedProduct(
        external_id=ext_id,
        name="x",
        url="https://example.com",
        current_price_minor=129900,
        original_price_minor=None,
        in_stock=True,
        currency="INR",
        scraped_at=datetime.now(UTC),
    )


@pytest.fixture
def session(monkeypatch):
    fake = FakeSession()
    monkeypatch.setattr(jobs, "SessionLocal", lambda: fake)
    return fake


@pytest.fixture
def calls(monkeypatch, session):
    log = []
    run = SimpleNamespace(id=1)
    monkeypatch.setattr(
        jobs.crud,
        "start_scrape_run",
        lambda session: (log.append(("start", run)), run)[1],
    )

    def fake_upsert(session, source, item, run):
        log.append(("upsert", source, item, run))

    def fake_finish(session, run, status, products_seen, error=None):
        log.append(("finish", status, products_seen, error))

    monkeypatch.setattr(jobs.crud, "upsert_product_and_snapshot", fake_upsert)
    monkeypatch.setattr(jobs.crud, "finish_scrape_run", fake_finish)
    return log


def test_happy_path_saves_all_and_returns_count(monkeypatch, calls):
    items = [make_item("a"), make_item("b")]

    def _happy_scrape(url):
        return items

    monkeypatch.setattr(jobs, "scrape", _happy_scrape)

    assert jobs.run_scrape_cycle() == 2
    assert [c[0] for c in calls] == ["start", "upsert", "upsert", "finish"]
    assert calls[1][1] == "demo-shop"
    assert [call[2] for call in calls[1:3]] == items
    assert all(call[3] is calls[0][1] for call in calls[1:3])
    assert calls[-1] == ("finish", "success", 2, None)


def test_empty_scrape_finishes_with_zero(monkeypatch, calls):
    def _empty_scrape(url):
        return []

    monkeypatch.setattr(jobs, "scrape", _empty_scrape)

    count = jobs.run_scrape_cycle()
    assert count == 0
    assert calls[-1] == ("finish", "success", 0, None)


def test_scrape_url_comes_from_settings(monkeypatch, calls):
    seen = {}

    def fake_scrape(url):
        seen["url"] = url
        return []

    monkeypatch.setattr(
        jobs, "settings", SimpleNamespace(scrape_target_url="https://example.com/list")
    )
    monkeypatch.setattr(jobs, "scrape", fake_scrape)

    jobs.run_scrape_cycle()
    assert seen["url"] == "https://example.com/list"


def test_failure_after_first_item_is_recorded_as_partial(monkeypatch, calls, session, caplog):
    items = [make_item("a"), make_item("b"), make_item("c")]
    monkeypatch.setattr(jobs, "scrape", lambda url: items)

    def flaky_upsert(session, source, item, run):
        if item.external_id == "b":
            raise RuntimeError("database error")
        calls.append(("upsert", source, item, run))

    monkeypatch.setattr(jobs.crud, "upsert_product_and_snapshot", flaky_upsert)

    assert jobs.run_scrape_cycle() == 2
    assert session.rollbacks == 1
    assert [call[2].external_id for call in calls if call[0] == "upsert"] == ["a", "c"]
    assert calls[-1] == ("finish", "partial", 2, "b: database error")
    assert any(record.exc_info for record in caplog.records)


def test_start_scrape_run_failure_does_not_raise(monkeypatch, calls, caplog):
    def boom(session):
        raise RuntimeError("database locked")

    monkeypatch.setattr(jobs.crud, "start_scrape_run", boom)

    assert jobs.run_scrape_cycle() == 0
    assert calls == []
    assert "Scrape cycle could not run" in caplog.text
    assert any(record.exc_info for record in caplog.records)


def test_finish_scrape_run_failure_does_not_raise(monkeypatch, calls, caplog):
    def scrape_boom(url):
        raise RuntimeError("site down")

    def finish_boom(session, run, status, products_seen, error=None):
        raise RuntimeError("database locked")

    monkeypatch.setattr(jobs, "scrape", scrape_boom)
    monkeypatch.setattr(jobs.crud, "finish_scrape_run", finish_boom)

    assert jobs.run_scrape_cycle() == 0
    assert "Could not finish scrape run" in caplog.text
    assert "Could not record failure for scrape run" in caplog.text
    assert any(record.exc_info for record in caplog.records)


def test_scrape_failure_finishes_run_as_failed(monkeypatch, calls, caplog):
    def scrape_boom(url):
        raise RuntimeError("site down")

    monkeypatch.setattr(jobs, "scrape", scrape_boom)

    assert jobs.run_scrape_cycle() == 0
    assert calls[-1] == ("finish", "failed", 0, "site down")
    assert any(record.exc_info for record in caplog.records)


@pytest.fixture
def real_database(monkeypatch):
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(jobs, "SessionLocal", session_factory)
    yield session_factory
    engine.dispose()


def test_scrape_cycle_persists_rows_with_real_crud(monkeypatch, real_database):
    items = [make_item("a"), make_item("b")]
    monkeypatch.setattr(jobs, "scrape", lambda url: items)

    assert jobs.run_scrape_cycle() == 2

    with real_database() as session:
        runs = list_scrape_runs(session)
        products = list_products(session)
        snapshots = session.scalars(
            select(PriceSnapshot).order_by(PriceSnapshot.current_price_minor)
        ).all()

    assert len(runs) == 1
    assert runs[0].status == "success"
    assert runs[0].products_seen == 2
    assert runs[0].finished_at is not None
    assert runs[0].error_message is None
    assert {product.external_id for product in products} == {"a", "b"}
    assert len(snapshots) == 2
    assert {snapshot.scrape_run_id for snapshot in snapshots} == {runs[0].id}
    assert {snapshot.current_price_minor for snapshot in snapshots} == {129900}
