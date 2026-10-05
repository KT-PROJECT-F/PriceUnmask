from datetime import datetime, timedelta, timezone

from backend.db.crud import (
    get_history,
    get_product,
    list_products,
    list_scrape_runs,
)
from backend.db.models import PriceSnapshot, ScrapeRun
from backend.devtools.seed_fake_data import seed


def test_list_products_returns_active_products(session):
    seed(session)

    products = list_products(session)

    assert products
    assert all(product.is_active for product in products)


def test_list_products_search_is_case_insensitive(session):
    seed(session)

    products = list_products(session, search="SPEAKER")

    assert len(products) == 1
    assert "speaker" in products[0].name.lower()


def test_list_products_does_not_return_inactive_products(session):
    seed(session)

    products = list_products(session)

    assert all(product.is_active for product in products)


def test_get_product_returns_product(session):
    seed(session)

    products = list_products(session)
    product = get_product(session, products[0].id)

    assert product is not None
    assert product.id == products[0].id


def test_get_product_unknown_id_returns_none(session):
    seed(session)

    product = get_product(session, 999999)

    assert product is None


def test_get_history_is_oldest_first(session):
    seed(session)

    products = list_products(session)
    product_id = products[0].id

    now = datetime.now(timezone.utc)

    old_snapshot = PriceSnapshot(
        product_id=product_id,
        scraped_at=now - timedelta(days=2),
        price_minor=10000,
    )

    new_snapshot = PriceSnapshot(
        product_id=product_id,
        scraped_at=now - timedelta(days=1),
        price_minor=9000,
    )

    session.add_all([new_snapshot, old_snapshot])
    session.commit()

    history = get_history(session, product_id)

    assert history[0].scraped_at <= history[1].scraped_at


def test_get_history_respects_since(session):
    seed(session)

    products = list_products(session)
    product_id = products[0].id

    now = datetime.now(timezone.utc)

    old_snapshot = PriceSnapshot(
        product_id=product_id,
        scraped_at=now - timedelta(days=2),
        price_minor=10000,
    )

    new_snapshot = PriceSnapshot(
        product_id=product_id,
        scraped_at=now - timedelta(days=1),
        price_minor=9000,
    )

    session.add_all([old_snapshot, new_snapshot])
    session.commit()

    since = now - timedelta(days=1, hours=12)

    history = get_history(session, product_id, since=since)

    assert len(history) == 1
    assert history[0].price_minor == 9000


def test_list_scrape_runs_newest_first_and_respects_limit(session):
    now = datetime.now(timezone.utc)

    run1 = ScrapeRun(
        started_at=now - timedelta(days=3),
    )

    run2 = ScrapeRun(
        started_at=now - timedelta(days=2),
    )

    run3 = ScrapeRun(
        started_at=now - timedelta(days=1),
    )

    session.add_all([run1, run2, run3])
    session.commit()

    runs = list_scrape_runs(session, limit=2)

    assert len(runs) == 2
    assert runs[0].started_at >= runs[1].started_at