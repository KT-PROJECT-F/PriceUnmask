from datetime import UTC, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import StatementError

from backend.db.models import PriceSnapshot, Product, ScrapeRun
from backend.devtools.seed_fake_data import seed
from backend.main import app


def test_health() -> None:
    with TestClient(app) as client:
        r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_schema_and_seed(session) -> None:
    seed(session)
    assert session.query(Product).count() == 3
    assert session.query(PriceSnapshot).count() > 100


def test_datetimes_are_stored_as_utc_and_come_back_aware(session) -> None:
    ist = timezone(timedelta(hours=5, minutes=30))
    started = datetime(2026, 10, 7, 15, 30, tzinfo=ist)  # 10:00 UTC
    run = ScrapeRun(started_at=started)
    session.add(run)
    session.commit()
    session.expire_all()  # force a real read from the database

    loaded = session.get(ScrapeRun, run.id)
    assert loaded.started_at.tzinfo == UTC
    assert loaded.started_at == started
    raw = session.execute(text("SELECT started_at FROM scrape_runs")).scalar_one()
    assert raw.startswith("2026-10-07 10:00:00")
    since = datetime(2026, 10, 7, 9, 0, tzinfo=UTC)
    assert session.scalars(select(ScrapeRun).where(ScrapeRun.started_at >= since)).all() == [loaded]


def test_naive_datetime_is_rejected(session) -> None:
    session.add(ScrapeRun(started_at=datetime(2026, 10, 7, 10, 0)))
    with pytest.raises(StatementError, match="naive datetime"):
        session.commit()
