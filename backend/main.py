"""FastAPI app. Owner: API track.

API lives under /api. The frontend folder is served at / by the same server,
so there is no CORS setup and one command runs everything:
    uvicorn backend.main:app --reload
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.db.database import init_db

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="PriceUnmask API", version="0.1.0", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# TODO(API track): add the endpoints listed in docs/ARCHITECTURE.md section 5:
#   GET  /api/products?search=
#   GET  /api/products/{product_id}
#   GET  /api/products/{product_id}/history
#   GET  /api/products/{product_id}/trust-score
#   GET  /api/scrape-runs
#   POST /api/scrape/run


# Mount the dashboard LAST so it does not shadow /api routes.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
