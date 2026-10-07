import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.database import Base, get_session
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
    assert response.json()["detail"] == "Product not found"


def test_get_product_bad_id(client):
    response = client.get("/api/products/abc")

    assert response.status_code == 422
