"""FastAPI app. Owner: API track.

API lives under /api. The frontend folder is served at / by the same server,
so there is no CORS setup and one command runs everything:
       uvicorn backend.main:app --reload
"""

from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, status
from fastapi import Path as FastAPIPath
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from backend import converters
from backend.analysis.anomaly_service import summarize_anomalies
from backend.analysis.trust_score import compute_trust_score
from backend.db import crud
from backend.db.database import get_session, init_db
from backend.scheduler.jobs import run_scrape_cycle_for_run
from backend.schemas import HistoryOut, ProductOut, ScrapeRunOut, TrustScoreOut

MAX_HISTORY_DAYS = 3650  # ten years; larger values would overflow datetime
MAX_SEARCH_LENGTH = 200
MAX_PRODUCT_ID = 2**63 - 1
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
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=MAX_SEARCH_LENGTH,
    ),
    session: Session = Depends(get_session),  # noqa: B008
) -> list[ProductOut]:
    # Direct lookup by ID can return inactive products.
    # The list endpoint only returns active products.
    products = crud.list_products(session, search=search)

    return [converters.product_to_out(product, product.snapshots) for product in products]


@app.get("/api/products/{product_id}", response_model=ProductOut)
def get_product(
    product_id: int = FastAPIPath(
        ge=1,
        le=MAX_PRODUCT_ID,
    ),
    session: Session = Depends(get_session),  # noqa: B008
) -> ProductOut:
    product = crud.get_product(session, product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return converters.product_to_out(product, product.snapshots)


@app.get(
    "/api/products/{product_id}/history",
    response_model=HistoryOut,
)
def get_product_history(
    product_id: int = FastAPIPath(
        ge=1,
        le=MAX_PRODUCT_ID,
    ),
    days: int | None = Query(default=None, ge=1, le=MAX_HISTORY_DAYS),
    session: Session = Depends(get_session),  # noqa: B008
) -> HistoryOut:

    product = crud.get_product(session, product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    since = None
    if days is not None:
        since = datetime.now(UTC) - timedelta(days=days)

    history = crud.get_history(session, product_id, since=since)

    return converters.history_to_out(product, history)


@app.get(
    "/api/products/{product_id}/trust-score",
    response_model=TrustScoreOut,
)
def get_product_trust_score(
    product_id: int = FastAPIPath(
        ge=1,
        le=MAX_PRODUCT_ID,
    ),
    session: Session = Depends(get_session),  # noqa: B008
) -> TrustScoreOut:
    product = crud.get_product(session, product_id)

    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    history = crud.get_history(session, product_id)
    history_df = converters.snapshots_to_dataframe(history)
    anomaly = summarize_anomalies(history_df)
    trust_score = compute_trust_score(history_df)

    signals = asdict(trust_score.signals) if trust_score.signals is not None else None

    return TrustScoreOut(
        product_id=product.id,
        score=trust_score.score,
        label=trust_score.label,
        reasons=trust_score.reasons,
        signals=signals,
        anomaly_status=anomaly.status,
        anomaly_result=anomaly.result,
        anomaly_message=anomaly.message,
    )


@app.get("/api/scrape-runs", response_model=list[ScrapeRunOut])
def get_scrape_runs(
    session: Session = Depends(get_session),  # noqa: B008
) -> list[ScrapeRunOut]:
    runs = crud.list_scrape_runs(session)
    return list(runs)


@app.post(
    "/api/scrape/run",
    response_model=ScrapeRunOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_scrape_run(
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),  # noqa: B008
) -> ScrapeRunOut:
    # If the server stops during a scrape, its run may remain "running".
    # New requests then return 409 until stale-run cleanup marks it failed.
    if crud.has_running_scrape_run(session):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A scrape run is already in progress",
        )

    run = crud.start_scrape_run(session)
    background_tasks.add_task(run_scrape_cycle_for_run, run.id)

    return run


# Mount the dashboard LAST so it does not shadow /api routes.
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
