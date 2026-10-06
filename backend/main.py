"""
FastAPI app. Owner: API track.

API lives under /api. The frontend folder is served at / by the same server.
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from backend.db.database import get_db, init_db
from backend.db.models import Product

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="PriceUnmask API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/products")
def get_products(db: Session = Depends(get_db)):  # noqa: B008
    products = db.query(Product).all()
    return products


# Mount the frontend LAST so it does not shadow /api routes.
app.mount(
    "/",
    StaticFiles(directory=FRONTEND_DIR, html=True),
    name="frontend",
)
