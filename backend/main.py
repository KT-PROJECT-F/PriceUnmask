"""FastAPI app. Owner: API track.

API lives under /api. The frontend folder is served at / by the same server,
so there is no CORS setup and one command runs everything:
    uvicorn backend.main:app --reload
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from backend import converters
from backend.db import crud
from backend.db.database import get_session, init_db
from backend.schemas import ProductOut

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="PriceUnmask API", version="0.1.0", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/products", response_model=list[ProductOut])
def list_products(
    search: str | None = Query(default=None),
    session: Session = Depends(get_session),  # noqa: B008
) -> list[ProductOut]:
    products = crud.list_products(session, search=search)

    return [converters.product_to_out(product, product.snapshots) for product in products]


@app.get("/api/products/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int,
    session: Session = Depends(get_session),  # noqa: B008
) -> ProductOut:
    product = crud.get_product(session, product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return converters.product_to_out(product, product.snapshots)


# TODO(API track): add the endpoints listed in docs/ARCHITECTURE.md section 5:
#   GET  /api/products?search=
#   GET  /api/products/{product_id}
#   GET  /api/products/{product_id}/history
#   GET  /api/products/{product_id}/trust-score
#   GET  /api/scrape-runs
#   POST /api/scrape/run


# Mount the dashboard LAST so it does not shadow /api routes.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
