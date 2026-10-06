from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

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


def test_start_scrape_run_creates_running_run(
    session: Session,
) -> None:
    run = start_scrape_run(session)

    assert run.id is not None
    assert run.status == "running"
    assert run.products_seen == 0
    assert run.finished_at is None


def test_finish_scrape_run_marks_run_success(
    session: Session,
) -> None:
    run = start_scrape_run(session)

    finished = finish_scrape_run(
        session,
        run,
        status="success",
        products_seen=3,
    )

    assert finished.id == run.id
    assert finished.status == "success"
    assert finished.products_seen == 3
    assert finished.finished_at is not None
    assert finished.error_message is None


def test_finish_scrape_run_stores_error(
    session: Session,
) -> None:
    run = start_scrape_run(session)

    finished = finish_scrape_run(
        session,
        run,
        status="failed",
        products_seen=1,
        error_message="Scraper failed",
    )

    assert finished.status == "failed"
    assert finished.products_seen == 1
    assert finished.error_message == "Scraper failed"
    assert finished.finished_at is not None


def make_scraped_product(
    *,
    external_id: str = "123",
    name: str = "Test Speaker",
    url: str = "https://example.com/speaker",
    price: int = 5000,
    original_price: int = 6000,
    in_stock: bool = True,
    scraped_at: datetime = NOW,
) -> SimpleNamespace:
    return SimpleNamespace(
        external_id=external_id,
        name=name,
        url=url,
        current_price_minor=price,
        original_price_minor=original_price,
        in_stock=in_stock,
        scraped_at=scraped_at,
    )


def test_upsert_new_product_creates_product_and_snapshot(
    session: Session,
) -> None:
    run = start_scrape_run(session)

    item = make_scraped_product()

    snapshot = upsert_product_and_snapshot(
        session,
        "amazon",
        item,
        run,
    )

    assert snapshot.id is not None
    assert snapshot.product_id is not None
    assert snapshot.current_price_minor == 5000

    product = get_product(session, snapshot.product_id)

    assert product is not None
    assert product.source == "amazon"
    assert product.external_id == "123"
    assert product.name == "Test Speaker"


def test_upsert_same_product_creates_one_product_and_two_snapshots(
    session: Session,
) -> None:
    run = start_scrape_run(session)

    first_item = make_scraped_product(
        price=5000,
    )

    first_snapshot = upsert_product_and_snapshot(
        session,
        "amazon",
        first_item,
        run,
    )

    second_item = make_scraped_product(
        price=4500,
        scraped_at=NOW + timedelta(minutes=5),
    )

    second_snapshot = upsert_product_and_snapshot(
        session,
        "amazon",
        second_item,
        run,
    )

    first_snapshot = upsert_product_and_snapshot(
        session,
        "amazon",
        first_item,
        run,
    )

    assert first_snapshot.product_id == second_snapshot.product_id

    assert first_snapshot.id != second_snapshot.id

    # There must be only one Product.
    products = list_products(session)

    matching_products = [
        product
        for product in products
        if product.source == "amazon" and product.external_id == "123"
    ]

    assert len(matching_products) == 1

    # There must be two snapshots.
    history = get_history(
        session,
        first_snapshot.product_id,
    )

    prices = [
        snapshot.current_price_minor
        for snapshot in history
        if snapshot.id
        in {
            first_snapshot.id,
            second_snapshot.id,
        }
    ]

    assert prices == [5000, 4500]


def test_existing_snapshot_is_never_modified(
    session: Session,
) -> None:
    run = start_scrape_run(session)

    first_item = make_scraped_product(
        name="Old Speaker",
        url="https://example.com/old",
        price=5000,
        original_price=6000,
        in_stock=True,
    )

    first_snapshot = upsert_product_and_snapshot(
        session,
        "amazon",
        first_item,
        run,
    )

    second_item = make_scraped_product(
        name="New Speaker",
        url="https://example.com/new",
        price=4000,
        original_price=5500,
        in_stock=False,
        scraped_at=NOW + timedelta(minutes=10),
    )

    second_snapshot = upsert_product_and_snapshot(
        session,
        "amazon",
        second_item,
        run,
    )

    session.refresh(first_snapshot)
    session.refresh(second_snapshot)

    # Old snapshot must stay unchanged.
    assert first_snapshot.current_price_minor == 5000
    assert first_snapshot.original_price_minor == 6000
    assert first_snapshot.in_stock is True

    # New snapshot contains the new values.
    assert second_snapshot.current_price_minor == 4000
    assert second_snapshot.original_price_minor == 5500
    assert second_snapshot.in_stock is False

    assert first_snapshot.id != second_snapshot.id


def test_upsert_updates_existing_product(
    session: Session,
) -> None:
    run = start_scrape_run(session)

    first_item = make_scraped_product(
        name="Old Speaker",
        url="https://example.com/old",
        price=5000,
    )

    first_snapshot = upsert_product_and_snapshot(
        session,
        "amazon",
        first_item,
        run,
    )

    second_item = make_scraped_product(
        name="New Speaker",
        url="https://example.com/new",
        price=4500,
        scraped_at=NOW + timedelta(minutes=5),
    )

    second_snapshot = upsert_product_and_snapshot(
        session,
        "amazon",
        second_item,
        run,
    )

    product = get_product(
        session,
        first_snapshot.product_id,
    )

    assert product is not None

    # Product gets updated.
    assert product.name == "New Speaker"
    assert product.url == "https://example.com/new"

    # Still the same Product.
    assert first_snapshot.product_id == second_snapshot.product_id


def test_same_external_id_with_different_source_creates_two_products(
    session: Session,
) -> None:
    run = start_scrape_run(session)

    item = make_scraped_product(
        external_id="123",
        price=5000,
    )

    amazon_snapshot = upsert_product_and_snapshot(
        session,
        "amazon",
        item,
        run,
    )

    flipkart_snapshot = upsert_product_and_snapshot(
        session,
        "flipkart",
        item,
        run,
    )

    # Same external_id is allowed because source is different.
    assert amazon_snapshot.product_id != flipkart_snapshot.product_id

    amazon_product = get_product(
        session,
        amazon_snapshot.product_id,
    )

    flipkart_product = get_product(
        session,
        flipkart_snapshot.product_id,
    )

    assert amazon_product is not None
    assert flipkart_product is not None

    assert amazon_product.source == "amazon"
    assert flipkart_product.source == "flipkart"
