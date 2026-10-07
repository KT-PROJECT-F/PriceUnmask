from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from backend.db.crud import (
    get_history,
    get_product,
    list_products,
    list_scrape_runs,
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
