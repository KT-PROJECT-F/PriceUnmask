from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from backend.db.crud import (
    finish_scrape_run,
    start_scrape_run,
    upsert_product_and_snapshot,
)
from backend.devtools.check_db import find_problems, report


def make_run(status: str = "success", products_seen: int = 24):
    return SimpleNamespace(
        id=7,
        status=status,
        products_seen=products_seen,
        finished_at=datetime.now(UTC),
    )


def test_old_successful_run_requires_attention() -> None:
    finished_at = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
    now = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
    run = make_run()
    run.finished_at = finished_at

    problems = find_problems(run, 24, 0, [], now=now)

    assert "latest finished run 7 is older than 24 hours" in problems


def test_recent_successful_run_is_not_stale() -> None:
    now = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
    run = make_run()
    run.finished_at = now - timedelta(hours=1)

    problems = find_problems(run, 24, 0, [], now=now)

    assert not any("older than 24 hours" in problem for problem in problems)


def test_healthy_run_has_no_problems() -> None:
    assert find_problems(make_run(), 24, 0, []) == []


def test_missing_snapshots_are_a_problem() -> None:
    problems = find_problems(make_run(products_seen=24), 12, 0, [])
    assert any("saved 12 snapshots but products_seen is 24" in problem for problem in problems)


def test_failed_run_and_unseen_products_are_problems() -> None:
    problems = find_problems(
        make_run(status="failed", products_seen=0),
        0,
        3,
        [],
    )
    assert any("status failed" in problem for problem in problems)
    assert any("3 products have no snapshot" in problem for problem in problems)


def test_duplicates_are_a_problem() -> None:
    problems = find_problems(make_run(), 24, 0, [("shop", "Phone", 2)])
    assert any("stored more than once" in problem for problem in problems)


def test_find_problems_uses_plural_for_two_duplicate_names():
    latest_run = SimpleNamespace(
        id=1,
        status="success",
        products_seen=0,
        finished_at=datetime(2026, 10, 12, 12, 0, tzinfo=UTC),
    )

    problems = find_problems(
        latest_run,
        0,
        0,
        [("shop", "Book A", 2), ("shop", "Book B", 2)],
    )

    assert "2 product names stored more than once" in problems


def test_report_prints_database_health(session, capsys):
    now = datetime(2026, 10, 12, 12, 0, tzinfo=UTC)

    run = start_scrape_run(session)

    for external_id in ("phone-a", "phone-b"):
        item = SimpleNamespace(
            external_id=external_id,
            name="Phone",
            url=f"https://example.com/{external_id}",
            current_price_minor=10_000,
            original_price_minor=None,
            in_stock=True,
            currency="INR",
            scraped_at=now,
        )
        upsert_product_and_snapshot(session, "shop", item, run)

    finish_scrape_run(session, run, "success", 2)

    report(session)
    output = capsys.readouterr().out

    assert "=== PriceUnmask Database Health ===" in output
    assert "Total products: 2" in output
    assert f"Run {run.id} (success): 2 snapshots, products_seen 2" in output
    assert "Duplicate product names:" in output
    assert "shop / Phone: 2 times" in output
    assert "Latest finished run:" in output
    assert f"ID: {run.id}" in output
    assert "Status: success" in output
    assert "Products without a snapshot in this run: 0" in output
    assert "Health status: CHECK REQUIRED" in output
    assert "1 product name stored more than once" in output


def test_report_flags_stale_running_run_without_changing_status(session, capsys, monkeypatch):
    from backend.devtools import check_db

    now = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
    started_at = now - timedelta(minutes=45)

    run = start_scrape_run(session)
    run.started_at = started_at
    session.commit()

    monkeypatch.setattr(check_db, "settings", SimpleNamespace(stale_run_minutes=30))
    monkeypatch.setattr(check_db, "datetime", SimpleNamespace(now=lambda tz=None: now))

    report(session)
    output = capsys.readouterr().out

    assert "Health status: CHECK REQUIRED" in output
    assert f"running run {run.id}" in output
    assert "45 minutes" in output
    assert run.status == "running"


def test_report_does_not_flag_recent_running_run_as_stale(session, capsys, monkeypatch):
    from backend.devtools import check_db

    now = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
    started_at = now - timedelta(minutes=5)

    run = start_scrape_run(session)
    run.started_at = started_at
    session.commit()

    monkeypatch.setattr(check_db, "settings", SimpleNamespace(stale_run_minutes=30))
    monkeypatch.setattr(check_db, "datetime", SimpleNamespace(now=lambda tz=None: now))

    report(session)
    output = capsys.readouterr().out

    assert "no finished scrape run found" in output
    assert "Health status: CHECK REQUIRED" in output
    assert "has been running for" not in output
    assert run.status == "running"


def test_report_flags_successful_run_with_zero_snapshots(session, capsys):
    run = start_scrape_run(session)
    finish_scrape_run(session, run, "success", 0)

    report(session)
    output = capsys.readouterr().out

    assert f"latest finished run {run.id} saved no snapshots" in output
    assert "Health status: CHECK REQUIRED" in output


def test_fresh_running_run_is_not_stale():
    from types import SimpleNamespace

    from backend.devtools.check_db import find_stale_running_problems

    now = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
    run = SimpleNamespace(
        id=1,
        status="running",
        started_at=now - timedelta(minutes=5),
    )

    assert find_stale_running_problems([run], now, 30) == []


def test_stale_running_run_reports_id_and_age():
    from types import SimpleNamespace

    from backend.devtools.check_db import find_stale_running_problems

    now = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
    started_at = now - timedelta(minutes=45)
    run = SimpleNamespace(
        id=7,
        status="running",
        started_at=started_at,
    )

    problems = find_stale_running_problems([run], now, 30)

    assert len(problems) == 1
    assert "running run 7" in problems[0]
    assert started_at.isoformat() in problems[0]
    assert "45 minutes" in problems[0]
