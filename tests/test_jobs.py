from datetime import UTC, datetime

import pytest

from backend.scheduler import jobs
from backend.scraper.product_scraper import ScrapedProduct


class FakeRun:
    id = 1


class FakeSession:
    def __enter__(self):
        return self

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
def calls(monkeypatch):
    log = []
    run = object()
    monkeypatch.setattr(jobs, "SessionLocal", lambda: FakeSession())
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


def test_source_key_and_url_passed(monkeypatch):
    seen = {}

    def fake_start(session):
        return FakeRun()

    def fake_scrape(url):
        seen["url"] = url
        return []

    def fake_upsert(session, source, item, run):
        return None

    def fake_finish(session, run, status, products_seen, error=None):
        return None

    monkeypatch.setattr(jobs, "SessionLocal", lambda: FakeSession())
    monkeypatch.setattr(jobs.crud, "start_scrape_run", fake_start)
    monkeypatch.setattr(jobs, "scrape", fake_scrape)
    monkeypatch.setattr(jobs.crud, "upsert_product_and_snapshot", fake_upsert)
    monkeypatch.setattr(jobs.crud, "finish_scrape_run", fake_finish)

    jobs.run_scrape_cycle()
    assert seen["url"] == jobs.settings.scrape_target_url


def test_scrape_error_is_recorded_and_logged(monkeypatch, calls, caplog):
    def boom(url):
        raise RuntimeError("site down")

    monkeypatch.setattr(jobs, "scrape", boom)

    assert jobs.run_scrape_cycle() == 0
    assert calls[-1] == ("finish", "failed", 0, "site down")
    assert "Scrape cycle failed" in caplog.text
