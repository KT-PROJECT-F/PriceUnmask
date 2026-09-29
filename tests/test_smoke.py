from fastapi.testclient import TestClient

from backend.db.models import PriceSnapshot, Product
from backend.devtools.seed_fake_data import seed
from backend.main import app


def test_health() -> None:
    with TestClient(app) as client:
        r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_schema_and_seed(session) -> None:
    seed(session)
    assert session.query(Product).count() == 3
    assert session.query(PriceSnapshot).count() > 100
