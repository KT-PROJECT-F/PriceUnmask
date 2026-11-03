# API Design Note

## What it does

The PriceUnmask API gives the frontend a consistent way to retrieve product information, price history, trust scores, anomaly results, and scrape-run status. Its endpoints live under `/api`, and FastAPI validates inputs and response shapes using the definitions in `backend/main.py` and `backend/schemas.py`. The API also provides a health endpoint and an endpoint to request a background scrape. The same FastAPI application serves the frontend from `/`, so the frontend and API can run together.

## Decisions

1. **Prices use integer minor units.** `ProductOut` and `PricePointOut` expose prices as integers, such as paise, rather than floating-point amounts. This avoids floating-point rounding problems; the frontend is responsible for formatting prices for display. See [`ProductOut`](https://github.com/KT-PROJECT-F/PriceUnmask/blob/feature/197-api-design-note/backend/schemas.py#L16) and [`PricePointOut`](https://github.com/KT-PROJECT-F/PriceUnmask/blob/feature/197-api-design-note/backend/schemas.py#L28).

2. **Starting a scrape returns `202 Accepted`.** The API creates a scrape run and schedules the scrape cycle as a background task instead of waiting for the entire scrape to finish. The response acknowledges that the request was accepted, not that scraping has completed. See [`start_scrape_run`](https://github.com/KT-PROJECT-F/PriceUnmask/blob/feature/197-api-design-note/backend/main.py#L154).

3. **A second active scrape returns `409 Conflict`.** Before checking for an active run, the API marks stale runs as failed. If a run is still in progress, the request returns `409`. This avoids starting overlapping runs and allows the API to recover from runs that have become stale. See [`start_scrape_run`](https://github.com/KT-PROJECT-F/PriceUnmask/blob/feature/197-api-design-note/backend/main.py#L154).

4. **The trust-score response exposes shopper-facing anomaly information.** `TrustScoreOut` includes the anomaly status, result, and message, along with the trust score, label, reasons, and signals. Internal detector notes are not part of the response contract. This keeps the API focused on information the frontend can present to shoppers. See [`TrustScoreOut`](https://github.com/KT-PROJECT-F/PriceUnmask/blob/feature/197-api-design-note/backend/schemas.py#L41) and [`get_product_trust_score`](https://github.com/KT-PROJECT-F/PriceUnmask/blob/feature/197-api-design-note/backend/main.py#L111).

5. **The API and frontend share one FastAPI application.** API routes use the `/api` prefix, while the frontend is mounted at `/`. This avoids a separate frontend server and CORS configuration for this setup. The frontend is mounted last so it does not shadow API routes. See the [frontend mount](https://github.com/KT-PROJECT-F/PriceUnmask/blob/feature/197-api-design-note/backend/main.py#L186).

## How it fails, and what happens then

FastAPI returns `422 Unprocessable Entity` when request parameters fail validation, such as an invalid product ID, an empty or overly long search term, or an invalid history period. Product detail, history, and trust-score requests return `404 Not Found` when the requested product does not exist. A scrape request returns `409 Conflict` when another run is still active and `500 Internal Server Error` if stale-run cleanup fails. The health endpoint returns `{"status": "ok"}` when the application is available.

## How it is tested

The API tests in [`tests/test_api.py`](../../tests/test_api.py) exercise successful responses, response shapes, input validation, and missing products. They also cover scrape-run behavior, including `202 Accepted`, `409 Conflict`, stale-run cleanup, and `500 Internal Server Error` when cleanup fails. The project checks include `ruff check .`, `ruff format --check .`, and `pytest -q`.

## Known limits and what we would do next

The scrape endpoint acknowledges work in the background, so the initial response does not report the final scrape result. Clients must query the scrape-runs endpoint to check progress and completion. The API currently uses fixed validation limits for search length, product IDs, and history periods. Future work could document and standardize error response schemas, improve scrape progress reporting, and expand contract tests whenever the public API changes.
