from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from backend.db.crud import (
    finish_scrape_run,
    get_history,
    get_product,
    list_products,
    list_scrape_runs,
    start_scrape_run,
    upsert_product_and_snapshot,
)
from backend.db.models import PriceSnapshot, Product, ScrapeRun
from backend.devtools.seed_fake_data import seed

NOW = datetime(2026, 10, 6, 12, 0, tzinfo=UTC)


def add_product(
    session: Session,
    name: str,
    *,
    active: bool = True,
) -> Product:
    product = Product(
        source="test",
        external_id=name,
        name=name,
        url=f"https://example.com/{name}",
        is_active=active,
    )
    session.add(product)
    session.commit()
    return product


def add_snapshot(
    session: Session,
    product: Product,
    days_ago: int,
    price: int,
) -> None:
    snapshot = PriceSnapshot(
        product_id=product.id,
        scraped_at=NOW - timedelta(days=days_ago),
        current_price_minor=price,
    )
    session.add(snapshot)
    session.commit()


def make_item(
    *,
    external_id: str = "p1",
    name: str = "Phone",
    price: int = 10_000,
    original: int | None = None,
    scraped_at: datetime = NOW,
):
    from types import SimpleNamespace

    return SimpleNamespace(
        external_id=external_id,
        name=name,
        url="https://example.com/p1",
        current_price_minor=price,
        original_price_minor=original,
        in_stock=True,
        currency="INR",
        scraped_at=scraped_at,
    )


def test_list_products_returns_active_products(session: Session) -> None:
    seed(session)

    products = list_products(session)

    assert products
    assert all(product.is_active for product in products)


def test_list_products_skips_inactive_products(session: Session) -> None:
    seed(session)
    add_product(session, "Hidden Speaker", active=False)

    products = list_products(session)

    names = [product.name for product in products]

    assert "Hidden Speaker" not in names
    assert len(products) == 3


def test_list_products_search_is_case_insensitive(session: Session) -> None:
    seed(session)

    products = list_products(session, search="SPEAKER")

    assert len(products) == 1
    assert products[0].name == "Demo Bluetooth Speaker (stable)"


def test_list_products_search_with_no_match_returns_empty(
    session: Session,
) -> None:
    seed(session)

    products = list_products(session, search="laptop")

    assert list(products) == []


def test_get_product_returns_product(session: Session) -> None:
    seed(session)

    products = list_products(session)
    product = get_product(session, products[0].id)

    assert product is not None
    assert product.id == products[0].id


def test_get_product_unknown_id_returns_none(session: Session) -> None:
    product = get_product(session, 999_999)

    assert product is None


def test_get_history_is_oldest_first(session: Session) -> None:
    product = add_product(session, "Kettle")

    add_snapshot(session, product, 1, 900)
    add_snapshot(session, product, 3, 1100)
    add_snapshot(session, product, 2, 1000)

    history = get_history(session, product.id)

    assert [snapshot.current_price_minor for snapshot in history] == [
        1100,
        1000,
        900,
    ]


def test_get_history_respects_since(session: Session) -> None:
    product = add_product(session, "Kettle")

    add_snapshot(session, product, 1, 900)
    add_snapshot(session, product, 3, 1100)
    add_snapshot(session, product, 2, 1000)

    since = NOW - timedelta(days=2)

    history = get_history(session, product.id, since=since)

    assert [snapshot.current_price_minor for snapshot in history] == [
        1000,
        900,
    ]


def test_get_history_only_returns_snapshots_for_that_product(
    session: Session,
) -> None:
    kettle = add_product(session, "Kettle")
    toaster = add_product(session, "Toaster")

    add_snapshot(session, kettle, 1, 900)
    add_snapshot(session, toaster, 1, 5000)

    history = get_history(session, kettle.id)

    assert [snapshot.current_price_minor for snapshot in history] == [900]


def test_list_scrape_runs_newest_first_and_respects_limit(
    session: Session,
) -> None:
    run1 = ScrapeRun(started_at=NOW - timedelta(days=3))
    run2 = ScrapeRun(started_at=NOW - timedelta(days=1))
    run3 = ScrapeRun(started_at=NOW - timedelta(days=2))

    session.add_all([run1, run2, run3])
    session.commit()

    runs = list_scrape_runs(session, limit=2)

    assert [run.id for run in runs] == [run2.id, run3.id]


def test_list_scrape_runs_default_limit_is_20(
    session: Session,
) -> None:
    session.add_all(
        [
            ScrapeRun(started_at=NOW - timedelta(hours=hours))
            for hours in range(25)
        ]
    )
    session.commit()

    runs = list_scrape_runs(session)

    assert len(runs) == 20


def test_start_scrape_run_is_running(session: Session) -> None:
    run = start_scrape_run(session)

    assert run.id is not None
    assert run.status == "running"
    assert run.finished_at is None


def test_finish_scrape_run_sets_fields(session: Session) -> None:
    run = start_scrape_run(session)

    finish_scrape_run(session, run, "failed", 0, error="boom")

    assert (run.status, run.products_seen, run.error_message) == (
        "failed",
        0,
        "boom",
    )
    assert run.finished_at is not None


def test_upsert_new_product_creates_one_product_one_snapshot(
    session: Session,
) -> None:
    run = start_scrape_run(session)

    upsert_product_and_snapshot(
        session,
        "shop",
        make_item(),
        run,
    )

    products = list_products(session)

    assert len(products) == 1
    assert len(get_history(session, products[0].id)) == 1


def test_upsert_same_product_twice_gives_one_product_two_snapshots(
    session: Session,
) -> None:
    run = start_scrape_run(session)

    first_time = NOW
    second_time = NOW + timedelta(minutes=1)

    upsert_product_and_snapshot(
        session,
        "shop",
        make_item(scraped_at=first_time),
        run,
    )

    upsert_product_and_snapshot(
        session,
        "shop",
        make_item(
            price=9_000,
            scraped_at=second_time,
        ),
        run,
    )

    products = list_products(session)

    assert len(products) == 1
    assert len(get_history(session, products[0].id)) == 2


def test_same_external_id_different_source_makes_two_products(
    session: Session,
) -> None:
    run = start_scrape_run(session)

    upsert_product_and_snapshot(
        session,
        "shop-a",
        make_item(),
        run,
    )

    upsert_product_and_snapshot(
        session,
        "shop-b",
        make_item(),
        run,
    )

    assert len(list_products(session)) == 2


def test_upsert_updates_name_but_keeps_one_product(
    session: Session,
) -> None:
    run = start_scrape_run(session)

    upsert_product_and_snapshot(
        session,
        "shop",
        make_item(name="Old"),
        run,
    )

    upsert_product_and_snapshot(
        session,
        "shop",
        make_item(
            name="New",
            scraped_at=NOW + timedelta(minutes=1),
        ),
        run,
    )

    products = list_products(session)

    assert len(products) == 1
    assert products[0].name == "New"


def test_second_upsert_does_not_change_first_snapshot(
    session: Session,
) -> None:
    run = start_scrape_run(session)

    first = upsert_product_and_snapshot(
        session,
        "shop",
        make_item(
            price=10_000,
            scraped_at=NOW,
        ),
        run,
    )

    before = (
        first.id,
        first.current_price_minor,
        first.original_price_minor,
        first.in_stock,
        first.scraped_at,
    )

    upsert_product_and_snapshot(
        session,
        "shop",
        make_item(
            price=5_000,
            scraped_at=NOW + timedelta(minutes=1),
        ),
        run,
    )

    session.expire_all()

    history = get_history(session, first.product_id)

    after = (
        history[0].id,
        history[0].current_price_minor,
        history[0].original_price_minor,
        history[0].in_stock,
        history[0].scraped_at,
    )

    assert before == after


def assert_aware_utc(value: datetime) -> None:
    assert value.tzinfo is not None
    assert value.utcoffset() is not None
    assert value.utcoffset().total_seconds() == 0
    assert value.tzinfo == UTC


def test_read_functions_return_aware_utc_timestamps(
    session: Session,
) -> None:
    run = start_scrape_run(session)

    snapshot = upsert_product_and_snapshot(
        session,
        "shop",
        make_item(),
        run,
    )
    product_id = snapshot.product_id

    # Force objects to reload values from the database.
    session.expire_all()

    products = list_products(session)
    product = get_product(session, product_id)
    history = get_history(session, product_id)
    runs = list_scrape_runs(session)

    assert product is not None
    assert products
    assert history
    assert runs

    assert_aware_utc(product.created_at)
    assert_aware_utc(product.last_seen_at)

    for item in products:
        assert_aware_utc(item.created_at)
        assert_aware_utc(item.last_seen_at)

    for item in history:
        assert_aware_utc(item.scraped_at)

    for item in runs:
        assert_aware_utc(item.started_at)
        if item.finished_at is not None:
            assert_aware_utc(item.finished_at)


def test_write_functions_return_aware_utc_timestamps(
    session: Session,
) -> None:
    run = start_scrape_run(session)

    assert_aware_utc(run.started_at)
    run_id = run.id

    session.expire_all()

    run = next(
        item for item in list_scrape_runs(session) if item.id == run_id
    )

    assert_aware_utc(run.started_at)

    snapshot = upsert_product_and_snapshot(
        session,
        "shop",
        make_item(),
        run,
    )

    assert_aware_utc(snapshot.scraped_at)

    snapshot_id = snapshot.id
    product_id = snapshot.product_id

    session.expire_all()

    snapshot = next(
        item for item in get_history(session, product_id) if item.id == snapshot_id
    )

    product = get_product(session, product_id)

    assert_aware_utc(snapshot.scraped_at)
    assert product is not None
    assert_aware_utc(product.created_at)
    assert_aware_utc(product.last_seen_at)

    finish_scrape_run(session, run, "success", 1)

    session.expire_all()

    run = next(
        item for item in list_scrape_runs(session) if item.id == run_id
    )

    assert_aware_utc(run.started_at)
    assert run.finished_at is not None
    assert_aware_utc(run.finished_at)


def test_get_history_rejects_naive_since(
    session: Session,
) -> None:
    product = add_product(session, "Kettle")
    naive_since = datetime(2026, 10, 1, 12, 0)

    with pytest.raises(ValueError, match="timezone-aware"):
        get_history(session, product.id, since=naive_since)


def test_get_history_ist_since_matches_equivalent_utc(
    session: Session,
) -> None:
    product = add_product(session, "Kettle")

    add_snapshot(session, product, 3, 1100)
    add_snapshot(session, product, 2, 1000)
    add_snapshot(session, product, 1, 900)

    ist = timezone(timedelta(hours=5, minutes=30))

    since_ist = datetime(2026, 10, 5, 12, 0, tzinfo=ist)
    since_utc = datetime(2026, 10, 5, 6, 30, tzinfo=UTC)

    history_ist = get_history(
        session,
        product.id,
        since=since_ist,
    )
    history_utc = get_history(
        session,
        product.id,
        since=since_utc,
    )

    assert [item.id for item in history_ist] == [
        item.id for item in history_utc
    ]