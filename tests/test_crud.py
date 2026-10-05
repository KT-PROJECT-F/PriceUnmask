from datetime import UTC, datetime, timedelta
from sqlalchemy import select 
from backend.db import crud
from backend.db.models import PriceSnapshot, Product, ScrapeRun
from backend.devtools.seed_fake_data import seed
 
 
def seed_products(session):
    seed(session)
 
 
def test_list_products_returns_active_products(session):
    seed_products(session)
 
    products = crud.list_products(session)
 
    assert len(products) == 3
    assert all(product.is_active for product in products)
 
 
def test_list_products_search_is_case_insensitive(session):
    seed_products(session)
 
    products = crud.list_products(session, search="SPEAKER")
 
    assert len(products) == 1
    assert "Speaker" in products[0].name
 
 
def test_list_products_does_not_return_inactive_product(session):
    seed_products(session)
 
    product = session.scalar(
        __import__("sqlalchemy").select(Product).where(
            Product.external_id == "demo-003"
        )
    )
    product.is_active = False
    session.commit()
 
    products = crud.list_products(session)
 
    assert len(products) == 2
    assert all(product.is_active for product in products)
 
 
def test_get_product_returns_product(session):
    seed_products(session)
 
    product = crud.get_product(session, 1)
 
    assert product is not None
    assert product.id == 1
 
 
def test_get_product_returns_none_for_unknown_id(session):
    seed_products(session)
 
    product = crud.get_product(session, 99999)
 
    assert product is None
 
 
def test_get_history_is_oldest_first(session):
    seed_products(session)
 
    product = crud.get_product(session, 1)
    history = crud.get_history(session, product.id)
 
    assert len(history) > 1
 
    dates = [snapshot.scraped_at for snapshot in history]
 
    assert dates == sorted(dates)
 
 
def test_get_history_respects_since(session):
    seed_products(session)
 
    product = crud.get_product(session, 1)
    all_history = crud.get_history(session, product.id)
 
    since = all_history[len(all_history) // 2].scraped_at
 
    filtered_history = crud.get_history(
        session,
        product.id,
        since=since,
    )
 
    assert len(filtered_history) < len(all_history)
    assert all(snapshot.scraped_at >= since for snapshot in filtered_history)
 
 
def test_get_history_unknown_product_returns_empty(session):
    history = crud.get_history(session, 99999)
 
    assert history == []
 
 
def test_list_scrape_runs_newest_first(session):
    now = datetime.now(UTC)
 
    run1 = ScrapeRun(
        started_at=now - timedelta(hours=3),
        status="success",
        products_seen=3,
    )
 
    run2 = ScrapeRun(
        started_at=now - timedelta(hours=2),
        status="success",
        products_seen=3,
    )
 
    run3 = ScrapeRun(
        started_at=now - timedelta(hours=1),
        status="success",
        products_seen=3,
    )
 
    session.add_all([run1, run2, run3])
    session.commit()
 
    runs = crud.list_scrape_runs(session)
 
    assert [run.id for run in runs] == [
        run3.id,
        run2.id,
        run1.id,
    ]
 
 
def test_list_scrape_runs_respects_limit(session):
    now = datetime.now(UTC)
 
    runs_to_add = [
        ScrapeRun(
            started_at=now - timedelta(hours=i),
            status="success",
            products_seen=3,
        )
        for i in range(5)
    ]
 
    session.add_all(runs_to_add)
    session.commit()
 
    runs = crud.list_scrape_runs(session, limit=2)
 
    assert len(runs) == 2