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


def override_get_session():
    with TestingSessionLocal() as session:
        yield session


def test_list_products(seeded_database):
    app.dependency_overrides[get_session] = override_get_session

    try:
        with TestClient(app) as client:
            response = client.get("/api/products")

        assert response.status_code == 200

        data = response.json()

        assert len(data) == 3
        names = {item["name"] for item in data}
        assert "Demo Bluetooth Speaker (stable)" in names
        assert "Demo Running Shoes (real drop)" in names
        assert "Demo Air Fryer (fake discount)" in names
    finally:
        app.dependency_overrides.clear()


def test_list_products_search(seeded_database):
    app.dependency_overrides[get_session] = override_get_session

    try:
        with TestClient(app) as client:
            response = client.get("/api/products?search=air")

        assert response.status_code == 200

        data = response.json()

        assert len(data) == 1
        assert data[0]["name"] == "Demo Air Fryer (fake discount)"
    finally:
        app.dependency_overrides.clear()


def test_get_product(seeded_database):
    app.dependency_overrides[get_session] = override_get_session

    try:
        with TestClient(app) as client:
            response = client.get("/api/products/3")

        assert response.status_code == 200

        data = response.json()

        assert data["id"] == 3
        assert data["name"] == "Demo Air Fryer (fake discount)"
    finally:
        app.dependency_overrides.clear()


def test_get_missing_product(seeded_database):
    app.dependency_overrides[get_session] = override_get_session

    try:
        with TestClient(app) as client:
            response = client.get("/api/products/999999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Product not found"
    finally:
        app.dependency_overrides.clear()
