from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.database import Base, get_session
from backend.db.models import PriceSnapshot, Product, ScrapeRun
from backend.devtools.seed_fake_data import seed
from backend.main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture
def seeded_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with TestingSessionLocal() as session:
        seed(session)
        yield


def override_get_session():
    with TestingSessionLocal() as session:
        yield session


@pytest.fixture
def client(seeded_database):
    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_list_products(client):
    response = client.get("/api/products")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 3

    names = {item["name"] for item in data}

    assert "Demo Bluetooth Speaker (stable)" in names
    assert "Demo Running Shoes (real drop)" in names
    assert "Demo Air Fryer (fake discount)" in names

    by_name = {item["name"]: item for item in data}

    fryer = by_name["Demo Air Fryer (fake discount)"]

    assert fryer["latest_price_minor"] == 104900
    assert fryer["lowest_price_minor"] <= fryer["latest_price_minor"]

    assert all(isinstance(item["latest_price_minor"], int) for item in data)


@pytest.mark.parametrize("term", ["shoes", "SHOES", "Shoes"])
def test_list_products_search(client, term):
    response = client.get(
        "/api/products",
        params={"search": term},
    )

    assert response.status_code == 200

    data = response.json()

    assert [item["name"] for item in data] == ["Demo Running Shoes (real drop)"]


def test_list_products_search_no_match(client):
    response = client.get(
        "/api/products",
        params={"search": "nothingmatches"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_list_products_search_empty(client):
    response = client.get(
        "/api/products",
        params={"search": ""},
    )

    assert response.status_code == 422


def test_list_products_search_too_long(client):
    response = client.get(
        "/api/products",
        params={"search": "a" * 201},
    )

    assert response.status_code == 422


def test_get_product(client):
    products_response = client.get("/api/products")

    assert products_response.status_code == 200

    products = products_response.json()

    fryer = next(item for item in products if item["name"] == "Demo Air Fryer (fake discount)")

    response = client.get(f"/api/products/{fryer['id']}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == fryer["id"]
    assert data["name"] == "Demo Air Fryer (fake discount)"


def test_get_missing_product(client):
    response = client.get("/api/products/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


def test_get_product_bad_id(client):
    response = client.get("/api/products/abc")

    assert response.status_code == 422


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/products/99999999999999999999",
        "/api/products/99999999999999999999/history",
        "/api/products/99999999999999999999/trust-score",
        "/api/products/9223372036854775808",
    ],
)
def test_product_endpoints_reject_huge_ids(client, endpoint):
    response = client.get(endpoint)
    assert response.status_code == 422


def test_get_product_largest_valid_id_is_404(client):
    response = client.get("/api/products/9223372036854775807")
    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


@pytest.mark.parametrize(
    "endpoint",
    [
        "/api/products/0",
        "/api/products/-1",
        "/api/products/0/history",
        "/api/products/-1/history",
        "/api/products/0/trust-score",
        "/api/products/-1/trust-score",
    ],
)
def test_product_endpoints_reject_non_positive_ids(client, endpoint):
    response = client.get(endpoint)

    assert response.status_code == 422


def test_get_product_history_oldest_first(client):
    products = client.get("/api/products").json()
    product_id = products[0]["id"]

    response = client.get(f"/api/products/{product_id}/history")

    assert response.status_code == 200

    data = response.json()

    assert data["product_id"] == product_id
    assert len(data["points"]) == 126

    timestamps = [point["scraped_at"] for point in data["points"]]

    assert timestamps == sorted(timestamps)


def test_get_product_history_days_filter(client):
    product_id = client.get("/api/products").json()[0]["id"]

    everything = client.get(f"/api/products/{product_id}/history").json()["points"]

    last_week = client.get(
        f"/api/products/{product_id}/history",
        params={"days": 7},
    ).json()["points"]

    cutoff = datetime.now(UTC) - timedelta(days=7)

    assert 0 < len(last_week) < len(everything)

    assert all(datetime.fromisoformat(point["scraped_at"]) >= cutoff for point in last_week)


def test_get_product_history_missing_product(client):
    response = client.get("/api/products/999999/history")

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


def test_get_product_history_without_snapshots_is_empty_not_404(client):
    with TestingSessionLocal() as session:
        product = Product(
            source="test",
            external_id="no-history",
            name="No History",
            url="https://example.com/no-history",
        )
        session.add(product)
        session.commit()
        product_id = product.id

    response = client.get(f"/api/products/{product_id}/history")

    assert response.status_code == 200
    assert response.json() == {"product_id": product_id, "points": []}


@pytest.mark.parametrize("days", [0, -1, -5, 3651, 100000, 1_000_000])
def test_get_product_history_invalid_days(client, days):
    product_id = client.get("/api/products").json()[0]["id"]

    response = client.get(
        f"/api/products/{product_id}/history",
        params={"days": days},
    )

    assert response.status_code == 422


def test_get_product_history_non_numeric_days(client):
    product_id = client.get("/api/products").json()[0]["id"]

    response = client.get(
        f"/api/products/{product_id}/history",
        params={"days": "abc"},
    )

    assert response.status_code == 422


def test_list_scrape_runs(client):
    with TestingSessionLocal() as session:
        session.add_all(
            [
                ScrapeRun(
                    started_at=datetime(2026, 1, 1, tzinfo=UTC),
                    finished_at=datetime(2026, 1, 1, 0, 5, tzinfo=UTC),
                    status="success",
                    products_seen=3,
                ),
                ScrapeRun(
                    started_at=datetime(2026, 1, 2, tzinfo=UTC),
                    finished_at=None,
                    status="running",
                    products_seen=2,
                ),
            ]
        )
        session.commit()

    response = client.get("/api/scrape-runs")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert data[0]["started_at"] > data[1]["started_at"]

    assert set(data[0]) == {
        "id",
        "started_at",
        "finished_at",
        "status",
        "products_seen",
        "error_message",
    }


def test_list_scrape_runs_empty(client):
    response = client.get("/api/scrape-runs")

    assert response.status_code == 200
    assert response.json() == []


def test_start_scrape_run_returns_202(client):
    with patch("backend.main.run_scrape_cycle_for_run") as mock_scrape:
        response = client.post("/api/scrape/run")

    assert response.status_code == 202

    data = response.json()
    assert data["id"] > 0
    assert data["status"] == "running"
    assert data["finished_at"] is None
    assert data["products_seen"] == 0
    assert data["error_message"] is None

    mock_scrape.assert_called_once_with(data["id"])


def test_start_scrape_run_returns_409_when_run_is_running(client):
    with TestingSessionLocal() as session:
        session.add(ScrapeRun(status="running", products_seen=0))
        session.commit()

    with patch("backend.main.run_scrape_cycle_for_run") as mock_scrape:
        response = client.post("/api/scrape/run")

    assert response.status_code == 409
    assert response.json() == {"detail": "A scrape run is already in progress"}
    mock_scrape.assert_not_called()


def test_list_scrape_runs_returns_at_most_20_newest_first(client):
    with TestingSessionLocal() as session:
        session.add_all(
            ScrapeRun(
                started_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=day),
                status="success",
                products_seen=day,
            )
            for day in range(25)
        )
        session.commit()

    data = client.get("/api/scrape-runs").json()

    assert len(data) == 20
    assert data[0]["products_seen"] == 24
    assert data[-1]["products_seen"] == 5


def test_get_product_trust_score_air_fryer(client):
    products = client.get("/api/products").json()
    fryer = next(item for item in products if item["name"] == "Demo Air Fryer (fake discount)")

    response = client.get(f"/api/products/{fryer['id']}/trust-score")

    assert response.status_code == 200

    data = response.json()

    assert data["product_id"] == fryer["id"]
    assert data["label"] == "likely_inflated"
    assert data["score"] is not None
    assert data["reasons"]
    assert data["signals"] is not None
    assert data["anomaly_status"] in {
        "insufficient_history",
        "normal",
        "unusual",
    }
    assert data["anomaly_result"] in {True, False, None}
    assert isinstance(data["anomaly_message"], str)
    assert "anomaly_note" not in data


def test_get_product_trust_score_insufficient_data(client):
    with TestingSessionLocal() as session:
        product = Product(
            source="test",
            external_id="insufficient-history",
            name="Insufficient History",
            url="https://example.com/insufficient-history",
        )
        session.add(product)
        session.commit()
        product_id = product.id

    response = client.get(f"/api/products/{product_id}/trust-score")

    assert response.status_code == 200

    data = response.json()

    assert data["product_id"] == product_id
    assert data["label"] == "insufficient_data"
    assert data["score"] is None
    assert data["signals"] is None
    assert data["reasons"]
    assert data["anomaly_status"] == "insufficient_history"
    assert data["anomaly_result"] is None
    assert data["anomaly_message"] == ("Not enough price history to detect unusual price changes.")


def test_get_product_trust_score_normal_price(client):
    with TestingSessionLocal() as session:
        product = Product(
            source="test",
            external_id="normal-price",
            name="Normal Price",
            url="https://example.com/normal-price",
        )
        session.add(product)
        session.flush()

        session.add_all(
            [
                PriceSnapshot(
                    product_id=product.id,
                    scraped_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=day),
                    current_price_minor=10000,
                    original_price_minor=None,
                    in_stock=True,
                )
                for day in range(6)
            ]
        )
        product_id = product.id
        session.commit()

    response = client.get(f"/api/products/{product_id}/trust-score")

    assert response.status_code == 200

    data = response.json()

    assert data["anomaly_status"] == "normal"
    assert data["anomaly_result"] is False
    assert data["anomaly_message"] == (
        "No unusual price changes detected. The price looks normal based on the available history."
    )


def test_get_product_trust_score_unusual_price(client):
    with TestingSessionLocal() as session:
        product = Product(
            source="test",
            external_id="unusual-price",
            name="Unusual Price",
            url="https://example.com/unusual-price",
        )
        session.add(product)
        session.flush()

        session.add_all(
            [
                PriceSnapshot(
                    product_id=product.id,
                    scraped_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=day),
                    current_price_minor=(15000 if day == 5 else 10000),
                    original_price_minor=None,
                    in_stock=True,
                )
                for day in range(6)
            ]
        )
        product_id = product.id
        session.commit()

    response = client.get(f"/api/products/{product_id}/trust-score")

    assert response.status_code == 200

    data = response.json()

    assert data["anomaly_status"] == "unusual"
    assert data["anomaly_result"] is True
    assert data["anomaly_message"] == (
        "An unusual price change was detected. "
        "Please review the price history before making a purchase."
    )


def test_get_product_trust_score_missing_product(client):
    response = client.get("/api/products/999999/trust-score")

    assert response.status_code == 404
    assert response.json() == {"detail": "Product not found"}


def test_get_product_trust_score_does_not_expose_anomaly_note(client):
    products = client.get("/api/products").json()

    for product in products:
        response = client.get(f"/api/products/{product['id']}/trust-score")

        assert response.status_code == 200

        data = response.json()
        assert "anomaly_status" in data
        assert "anomaly_result" in data
        assert "anomaly_message" in data
        assert "anomaly_note" not in data
