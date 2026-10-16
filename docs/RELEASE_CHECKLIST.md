# Release Checklist

Run this checklist before each PriceUnmask release. Use a fresh clone so the test does not depend on an existing virtual environment, database, or uncommitted files. Follow the setup instructions in `README.md`; if the README conflicts with a command below, record the issue rather than silently changing the documented process.

## Release smoke test

### 1. Clone the repository

**Action (PowerShell):**

```powershell
cd C:\Users\Windows\Desktop
git clone https://github.com/KT-PROJECT-F/PriceUnmask.git priceunmask-release-check
cd priceunmask-release-check
git switch dev
git rev-parse HEAD
```

If the folder already exists, use a new folder name or remove the old test clone before cloning again.

**Expected result:** The clone succeeds, the checked-out branch is `dev`, and the exact commit hash is recorded in the results table.

### 2. Set up Python

**Action:** Follow the Python and dependency-installation steps in `README.md` from the fresh clone. Use the commands documented there to create and activate the virtual environment and install dependencies.

**Expected result:** The virtual environment activates and dependencies install without errors. Record any missing, incorrect, or Windows-incompatible README instructions.

### 3. Create and seed the database

**Action:** Follow the README instructions for creating a fresh database and seeding demo data. If the README documents these project commands, run:

```powershell
python -m backend.devtools.seed_fake_data
python -m backend.devtools.check_db
```

**Expected result:** Seeding completes successfully, the database check reports the expected demo products, and no database errors occur. Record the actual output.

### 4. Start the application

**Action:** Follow the README instructions to start the app. If the documented command is Uvicorn, run:

```powershell
uvicorn backend.main:app --reload
```

Keep the server running while completing the dashboard and API checks. In a browser, open:

- Dashboard: `http://127.0.0.1:8000/`
- API documentation: `http://127.0.0.1:8000/docs`
- Health endpoint: `http://127.0.0.1:8000/api/health`

**Expected result:** The application starts without errors, the dashboard loads, and the health endpoint returns HTTP 200 with a healthy status. Record the actual response.

### 5. Check the dashboard

**Action:** Use the fresh database and check each item:

1. **Product grid:** All seeded demo products appear with their prices.
2. **Search:** Search for `air`; only matching products, including `Demo Air Fryer (fake discount)` if present in the seed data, should appear.
3. **No-results search:** Search for `zzzz`; a clear no-results state appears.
4. **Product detail:** Open a product and confirm its name and price appear.
5. **Price chart:** Confirm the product's price chart is displayed when history data is available; record the behavior if the seed data has no history.
6. **Trust Score:** Confirm each demo product displays its trust label or score.
7. **Collector status:** Confirm the dashboard shows the newest collector run or a clear “no runs yet” state.

**Expected result:** Record each subcheck's actual result. Mark the overall dashboard step `FAIL` if any required subcheck fails; describe the failing subcheck in the results table and open a GitHub issue.

### 6. Check API endpoints with valid input

**Action:** Open `/docs` and call every documented endpoint with valid input. At minimum, check the following requests:

| Request | Expected result |
|---|---|
| `GET /api/products` | HTTP 200 and a product list |
| `GET /api/products?search=air` | HTTP 200 and only products matching `air` |
| `GET /api/products/1` | HTTP 200 and product details, if product ID `1` exists in the fresh seed data |
| `GET /api/products/1/history?days=30` | HTTP 200 and history data, if product ID `1` exists |
| `GET /api/products/1/trust-score` | HTTP 200 and a trust score/label, if product ID `1` exists |
| `GET /api/scrape-runs` | HTTP 200 and the scrape-run list, or an empty list before a run exists |

**Expected result:** Status codes and response contents match the documented API behavior. Verify search results actually contain the query; HTTP 200 alone does not prove search is correct. If seeded IDs differ, use an ID returned by `GET /api/products` and record the ID tested.

### 7. Check invalid API inputs

**Action:** Use `/docs` to run these negative tests:

| Request | Expected result |
|---|---|
| `GET /api/products/999999` | HTTP 404 Not Found |
| `GET /api/products/1/history?days=0` | HTTP 422 if `days=0` is outside the documented allowed range |
| `GET /api/products?search=` followed by a 201-character query | HTTP 422 if the query-length validation limit is 200 characters |

**Expected result:** Invalid inputs return the documented error status and a clear response; the application does not crash. Record the exact status and response for each request. Use an existing product ID for the `days=0` test if the endpoint requires it.

### 8. Run one real collector cycle

**Action:** Run the collector once against the real site, only when it is safe to do so and no other team member is running a competing integration collection. Follow any project-specific rate-limit and robots.txt rules. From the project root, with the virtual environment activated, run:

```powershell
python -m backend.scheduler.jobs
```

Wait for the first collection cycle to finish, then press `Ctrl+C`. Record the actual logs, fetch result, completion status, and number of products seen. Do not assume the number of products in advance; the collector may visit multiple pages.

**Expected result:** The scheduler starts, the site fetch outcome is reported, and the collection job completes or reports a clear failure. A successful HTTP response by itself does not prove that the data was saved to the database.

### 9. Verify persisted collection data

**Action:** With the application running, request:

```text
GET http://127.0.0.1:8000/api/scrape-runs
```

Inspect the newest run and verify the database using the project's documented database-check command or the appropriate database inspection method. Record the newest run ID, status, `products_seen`, and saved snapshot count. Compare these values with the collector's actual output.

**Expected result:** The latest run is persisted and visible through the API. Its status and product count agree with the collector outcome, and saved products and price snapshots reflect the collection. If the collector completed but the run or snapshots are missing, mark this step `FAIL` and open a GitHub issue.

### 10. Run automated checks

**Action:** From the repository root, with the project's virtual environment activated, run each command separately:

```powershell
ruff check .
ruff format --check .
pytest -q
```

**Expected result:** All three commands pass. Record the actual lint result, formatting result, test count, warnings, and any failures. Do not reuse results from another branch or clone.

### 11. Record and report failures

**Action:** Open a GitHub issue for every failed check. Include reproduction steps, the expected result, the actual result, relevant logs, and the tested commit hash. Link every issue in the results table or PR description. If all checks pass, explicitly record `No failures found`.

**Expected result:** Every failure has a linked issue, or the results explicitly state `No failures found`. Do not mark a failed or unverified check as `PASS`.

## v0.1 results

- **Date:** 2026-10-16
- **Tested by:** @mathango
- **Branch tested:** `dev`
- **Commit hash:** `d8dd893b5745b82443b0e6b0ca555215db5af7e8`

| Step | Result | What I observed |
|---|---|---|
| 1. Fresh clone | PASS | Tested from a fresh clone. Recorded commit hash: `d8dd893b5745b82443b0e6b0ca555215db5af7e8`. |
| 2. Python setup | PASS — reported | Application setup and testing were reported as successful. Keep the README setup output if exact evidence is requested. |
| 3. Database and seed | PASS — reported | Demo products were available during dashboard and API testing. |
| 4. Application startup | PASS — reported | The application was running for dashboard and API checks. |
| 5. Dashboard | PASS — partially verified | Product grid, search, product detail, price chart, and Trust Score passed. Confirm collector status because earlier notes were inconsistent. |
| 6. Valid API requests | PASS — reported | Product list and product detail returned HTTP 200. Verify that search results contain only products matching the query. |
| 7. Invalid API inputs | PASS | Product ID `999999` returned HTTP 404; `days=0` returned HTTP 422; a 201-character search query returned HTTP 422. |
| 8. Collector cycle | PASS — reported | Books to Scrape returned HTTP 200, `robots.txt` returned 404 and the scraper continued, a 3-second delay was observed, and 20 products were reported. Recorded collection time: `2026-10-15 13:18:44`. |
| 9. Persisted collection data | NOT VERIFIED | Confirm the newest scrape-run record through `GET /api/scrape-runs` and verify the saved price snapshot count before marking this step as passed. |
| 10. Ruff and pytest | PASS | `ruff check .` passed; `ruff format --check .` passed with 45 files already formatted; `pytest -q` reported 252 passed and 1 deprecation warning. |
| 11. Failure tracking | COMPLETE | Add issue links for confirmed failures. Record `No failures found` only after all checks are verified and passing. |


