from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from backend.db.crud import (
    count_products,
    count_runs_by_status,
    count_snapshots_by_run,
    finish_scrape_run,
    get_history,
    get_product,
    list_duplicate_product_names,
    list_products,
    list_products_not_seen_in_run,
    list_scrape_runs,
    mark_stale_runs_failed,
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
    session.add_all([ScrapeRun(started_at=NOW - timedelta(hours=hours)) for hours in range(25)])
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
        make_item(price=9_000, scraped_at=second_time),
        run,
    )

    products = list_products(session)

    assert len(products) == 1
    assert len(get_history(session, products[0].id)) == 2


def test_same_external_id_with_new_name_preserves_history(
    session: Session,
) -> None:
    first_run = start_scrape_run(session)
    first = upsert_product_and_snapshot(
        session,
        "shop",
        make_item(
            external_id="book-001",
            name="Old Book Name",
            price=1000,
            scraped_at=NOW,
        ),
        first_run,
    )

    before = (
        first.id,
        first.current_price_minor,
        first.scrape_run_id,
        first.scraped_at,
    )

    second_run = start_scrape_run(session)
    upsert_product_and_snapshot(
        session,
        "shop",
        make_item(
            external_id="book-001",
            name="New Book Name",
            price=900,
            scraped_at=NOW + timedelta(hours=4),
        ),
        second_run,
    )

    session.expire_all()

    products = list_products(session)
    assert len(products) == 1
    assert products[0].name == "New Book Name"

    history = get_history(session, products[0].id)
    assert [item.current_price_minor for item in history] == [1000, 900]

    after = (
        history[0].id,
        history[0].current_price_minor,
        history[0].scrape_run_id,
        history[0].scraped_at,
    )
    assert before == after


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
        make_item(price=10_000, scraped_at=NOW),
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

    run = next(item for item in list_scrape_runs(session) if item.id == run_id)

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

    snapshot = next(item for item in get_history(session, product_id) if item.id == snapshot_id)

    product = get_product(session, product_id)

    assert_aware_utc(snapshot.scraped_at)
    assert product is not None
    assert_aware_utc(product.created_at)
    assert_aware_utc(product.last_seen_at)

    finish_scrape_run(session, run, "success", 1)

    session.expire_all()

    run = next(item for item in list_scrape_runs(session) if item.id == run_id)

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

    assert [item.id for item in history_ist] == [item.id for item in history_utc]


def test_counts_and_products_not_seen_in_run(session: Session) -> None:
    first = start_scrape_run(session)

    upsert_product_and_snapshot(
        session,
        "shop",
        make_item(external_id="a", name="Alpha"),
        first,
    )
    upsert_product_and_snapshot(
        session,
        "shop",
        make_item(external_id="b", name="Beta"),
        first,
    )

    finish_scrape_run(session, first, "success", 2)

    later = NOW + timedelta(hours=4)
    second = start_scrape_run(session)

    upsert_product_and_snapshot(
        session,
        "shop",
        make_item(
            external_id="a",
            name="Alpha",
            scraped_at=later,
        ),
        second,
    )

    finish_scrape_run(session, second, "partial", 1)

    assert count_products(session) == 2
    assert count_runs_by_status(session) == {"success": 1, "partial": 1}
    assert count_snapshots_by_run(session) == {
        first.id: 2,
        second.id: 1,
    }
    assert [product.name for product in list_products_not_seen_in_run(session, second.id)] == [
        "Beta"
    ]
    assert list_products_not_seen_in_run(session, first.id) == []


def test_duplicate_product_names_are_reported(session: Session) -> None:
    run = start_scrape_run(session)

    upsert_product_and_snapshot(
        session,
        "shop",
        make_item(external_id="a", name="Phone"),
        run,
    )
    upsert_product_and_snapshot(
        session,
        "shop",
        make_item(external_id="b", name="Phone"),
        run,
    )
    upsert_product_and_snapshot(
        session,
        "shop",
        make_item(external_id="c", name="Laptop"),
        run,
    )

    assert list_duplicate_product_names(session) == [("shop", "Phone", 2)]


def test_no_duplicates_when_names_are_different(session: Session) -> None:
    run = start_scrape_run(session)

    upsert_product_and_snapshot(
        session,
        "shop",
        make_item(external_id="a", name="Phone"),
        run,
    )
    upsert_product_and_snapshot(
        session,
        "shop",
        make_item(external_id="b", name="Laptop"),
        run,
    )

    assert list_duplicate_product_names(session) == []


def test_snapshot_without_original_price(session: Session) -> None:
    run = start_scrape_run(session)
    item = make_item(external_id="book-002", price=1000)

    snapshot = upsert_product_and_snapshot(
        session,
        "shop",
        item,
        run,
    )

    assert snapshot.current_price_minor == 1000
    assert snapshot.original_price_minor is None

    history = get_history(session, snapshot.product_id)
    assert len(history) == 1
    assert history[0].original_price_minor is None


def test_run_with_zero_products_keeps_history_and_reports_missing(
    session: Session,
) -> None:
    first_run = start_scrape_run(session)
    snapshot = upsert_product_and_snapshot(
        session,
        "shop",
        make_item(external_id="book-004", name="Alpha", scraped_at=NOW),
        first_run,
    )
    finish_scrape_run(session, first_run, "success", 1)

    empty_run = start_scrape_run(session)
    finish_scrape_run(session, empty_run, "success", 0)

    assert count_runs_by_status(session) == {"success": 2}
    assert count_snapshots_by_run(session) == {first_run.id: 1}
    assert [product.name for product in list_products_not_seen_in_run(session, empty_run.id)] == [
        "Alpha"
    ]
    assert len(get_history(session, snapshot.product_id)) == 1


def test_get_history_returns_empty_for_product_without_snapshots(
    session: Session,
) -> None:
    product = add_product(session, "Product Without History")

    history = get_history(session, product.id)

    assert history == []


def test_same_product_saved_in_two_runs_creates_two_snapshots(
    session: Session,
) -> None:
    first_run = start_scrape_run(session)
    first_snapshot = upsert_product_and_snapshot(
        session,
        "shop",
        make_item(
            scraped_at=NOW,
            external_id="book-003",
            price=1000,
        ),
        first_run,
    )

    second_run = start_scrape_run(session)
    second_snapshot = upsert_product_and_snapshot(
        session,
        "shop",
        make_item(
            scraped_at=NOW + timedelta(hours=4),
            external_id="book-003",
            price=800,
        ),
        second_run,
    )

    products = list_products(session)
    history = get_history(session, first_snapshot.product_id)

    assert len(products) == 1
    assert first_snapshot.id != second_snapshot.id
    assert len(history) == 2
    assert [item.current_price_minor for item in history] == [1000, 800]
    assert [item.scrape_run_id for item in history] == [
        first_run.id,
        second_run.id,
    ]


def add_run(
    session: Session,
    *,
    status: str = "running",
    started_at: datetime,
    finished_at: datetime | None = None,
    error_message: str | None = None,
) -> ScrapeRun:
    """Create a scrape run with fixed timestamps for testing."""
    run = ScrapeRun(
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        error_message=error_message,
        products_seen=0,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def test_mark_one_stale_run_failed(session: Session) -> None:
    run = add_run(
        session,
        started_at=NOW - timedelta(minutes=45),
    )

    changed = mark_stale_runs_failed(
        session,
        older_than=timedelta(minutes=30),
        now=NOW,
    )

    session.refresh(run)

    assert changed == 1
    assert run.status == "failed"
    assert run.finished_at == NOW
    assert run.error_message is not None
    assert "stale" in run.error_message.lower()
    assert run.started_at == NOW - timedelta(minutes=45)


def test_run_started_exactly_at_the_threshold_is_not_stale(
    session: Session,
) -> None:
    run = add_run(
        session,
        started_at=NOW - timedelta(minutes=30),
    )

    changed = mark_stale_runs_failed(
        session,
        older_than=timedelta(minutes=30),
        now=NOW,
    )

    session.refresh(run)

    # Exactly 30 minutes is not more than 30 minutes ago.
    assert changed == 0
    assert run.status == "running"


def test_mark_fresh_run_keeps_running(session: Session) -> None:
    run = add_run(
        session,
        started_at=NOW - timedelta(minutes=5),
    )

    changed = mark_stale_runs_failed(
        session,
        older_than=timedelta(minutes=30),
        now=NOW,
    )

    session.refresh(run)

    assert changed == 0
    assert run.status == "running"
    assert run.finished_at is None
    assert run.error_message is None


def test_mark_stale_does_not_change_success_run(
    session: Session,
) -> None:
    finished_at = NOW - timedelta(minutes=20)

    run = add_run(
        session,
        status="success",
        started_at=NOW - timedelta(hours=2),
        finished_at=finished_at,
    )

    changed = mark_stale_runs_failed(
        session,
        older_than=timedelta(minutes=30),
        now=NOW,
    )

    session.refresh(run)

    assert changed == 0
    assert run.status == "success"
    assert run.finished_at == finished_at
    assert run.error_message is None


def test_mark_stale_runs_when_database_is_empty(
    session: Session,
) -> None:
    changed = mark_stale_runs_failed(
        session,
        older_than=timedelta(minutes=30),
        now=NOW,
    )

    assert changed == 0


def test_mark_two_stale_runs_failed(session: Session) -> None:
    first = add_run(
        session,
        started_at=NOW - timedelta(minutes=45),
    )
    second = add_run(
        session,
        started_at=NOW - timedelta(hours=2),
    )

    changed = mark_stale_runs_failed(
        session,
        older_than=timedelta(minutes=30),
        now=NOW,
    )

    session.refresh(first)
    session.refresh(second)

    assert changed == 2

    for run in (first, second):
        assert run.status == "failed"
        assert run.finished_at == NOW
        assert run.error_message is not None
        assert "stale" in run.error_message.lower()


@pytest.mark.parametrize("status", ["failed", "partial"])
def test_mark_stale_does_not_change_failed_or_partial_runs(
    session: Session,
    status: str,
) -> None:
    finished_at = NOW - timedelta(hours=1)

    run = add_run(
        session,
        status=status,
        started_at=NOW - timedelta(hours=2),
        finished_at=finished_at,
        error_message="Original error",
    )

    changed = mark_stale_runs_failed(
        session,
        older_than=timedelta(minutes=30),
        now=NOW,
    )

    session.refresh(run)

    assert changed == 0
    assert run.status == status
    assert run.finished_at == finished_at
    assert run.error_message == "Original error"


def test_mark_stale_does_not_modify_snapshots(
    session: Session,
) -> None:
    run = start_scrape_run(session)

    snapshot = upsert_product_and_snapshot(
        session,
        "shop",
        make_item(scraped_at=NOW),
        run,
    )

    original_snapshot = (
        snapshot.id,
        snapshot.product_id,
        snapshot.scrape_run_id,
        snapshot.scraped_at,
        snapshot.current_price_minor,
        snapshot.original_price_minor,
        snapshot.in_stock,
    )

    # Make the run stale using a fixed UTC timestamp.
    run.started_at = NOW - timedelta(hours=1)
    session.commit()

    changed = mark_stale_runs_failed(
        session,
        older_than=timedelta(minutes=30),
        now=NOW,
    )

    session.expire_all()

    saved_run = session.get(ScrapeRun, run.id)
    saved_snapshot = session.get(PriceSnapshot, snapshot.id)

    assert changed == 1
    assert saved_run is not None
    assert saved_run.status == "failed"

    assert saved_snapshot is not None
    assert (
        saved_snapshot.id,
        saved_snapshot.product_id,
        saved_snapshot.scrape_run_id,
        saved_snapshot.scraped_at,
        saved_snapshot.current_price_minor,
        saved_snapshot.original_price_minor,
        saved_snapshot.in_stock,
    ) == original_snapshot


def test_list_products_search_percent_matches_literal_character(
    session: Session,
) -> None:
    add_product(session, "100% Python")
    add_product(session, "Python Book")
    add_product(session, "Java Book")

    products = list_products(session, search="%")

    assert [product.name for product in products] == ["100% Python"]


def test_list_products_search_underscore_matches_literal_character(
    session: Session,
) -> None:
    add_product(session, "Python_Book")
    add_product(session, "Python Book")
    add_product(session, "Java Book")

    products = list_products(session, search="_")

    assert [product.name for product in products] == ["Python_Book"]


def test_list_products_search_100_percent_matches_literal_text(
    session: Session,
) -> None:
    add_product(session, "100% Python")
    add_product(session, "100 Python")
    add_product(session, "Python 100")

    products = list_products(session, search="100%")

    assert [product.name for product in products] == ["100% Python"]


def test_list_products_search_escape_character_matches_literally(
    session: Session,
) -> None:
    add_product(session, "Python/Book")
    add_product(session, "Python Book")

    products = list_products(session, search="/")

    assert [product.name for product in products] == ["Python/Book"]
