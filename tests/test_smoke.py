from datetime import UTC, datetime, timedelta, timezone

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from backend.analysis.trust_score import compute_signals
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


def test_compute_signals_basic_history() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.to_datetime(
                [
                    "2026-10-01 10:00:00+00:00",
                    "2026-10-02 10:00:00+00:00",
                    "2026-10-03 10:00:00+00:00",
                    "2026-10-04 10:00:00+00:00",
                    "2026-10-05 10:00:00+00:00",
                ]
            ),
            "current_price_minor": [1000, 900, 1100, 800, 1000],
            "original_price_minor": [1500, 1500, 1500, 1500, 1500],
        }
    )

    signals = compute_signals(history)

    assert signals.snapshot_count == 5
    assert signals.days_of_history == 4
    assert signals.lowest_price_minor == 800
    assert signals.pct_above_lowest == 25.0


def test_compute_signals_constant_price() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.to_datetime(
                [
                    "2026-10-01 10:00:00+00:00",
                    "2026-10-02 10:00:00+00:00",
                    "2026-10-03 10:00:00+00:00",
                ]
            ),
            "current_price_minor": [1000, 1000, 1000],
            "original_price_minor": [1500, 1500, 1500],
        }
    )

    signals = compute_signals(history)

    assert signals.lowest_price_minor == 1000
    assert signals.pct_above_lowest == 0.0
    assert signals.volatility_pct == 0.0
