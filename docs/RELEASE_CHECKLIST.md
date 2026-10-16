# Release checklist

Run this before every release, on a **fresh clone** in a new folder, so nothing
from your own working copy (venv, `.env`, database) can hide a problem. It takes
about 30 minutes. Write what you see in the results table at the bottom.

Rules for the results:

- Write only what you saw on your screen during this run.
- `PASS` only when the expected result happened. `FAIL` if it did not.
  `NOT RUN` if you skipped the step.
- Every `FAIL` gets a GitHub issue, linked in the table.

## Steps

### 1. Fresh clone

```powershell
cd $HOME\Desktop
git clone https://github.com/KT-PROJECT-F/PriceUnmask.git priceunmask-release-check
cd priceunmask-release-check
git switch dev
git rev-parse HEAD
```

If the folder already exists, delete it first or use a new name.

**Expected:** the clone works, you are on `dev`, and `git rev-parse HEAD` prints
the commit hash. Write the hash in the results.

### 2. Python setup

Follow `README.md`. On Windows PowerShell the README's
`source .venv/bin/activate` does not work. Use:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt
Copy-Item .env.example .env
python --version
```

**Expected:** the prompt starts with `(.venv)`, and `pip install` ends without
errors. Write down every place where the README was wrong or missing a step.

### 3. Seed fake data

```powershell
python -m backend.devtools.seed_fake_data
python -m backend.devtools.check_db
```

**Expected:**

- The seed prints `Seeded 3 fake products.`
- `check_db` shows `Total products: 3`, and `Health status: CHECK REQUIRED` with
  the reason `no finished scrape run found`. That is correct: there are no
  runs yet.

### 4. Start the app

```powershell
uvicorn backend.main:app --reload
```

Leave this terminal open. Open http://127.0.0.1:8000/api/health

**Expected:** `{"status":"ok"}`

### 5. Dashboard

Open http://127.0.0.1:8000/

| **Check**        | **Expected**                                                                                                |
| ---------------- | ----------------------------------------------------------------------------------------------------------- |
| Product grid     | 3 products: Demo Bluetooth Speaker (stable), Demo Running Shoes (real drop), Demo Air Fryer (fake discount) |
| Search `air`     | only Demo Air Fryer (fake discount)                                                                         |
| Search `zzzz`    | "No products match your search."                                                                            |
| Click a product  | detail view with its name, price and a price chart                                                          |
| Trust Score      | Speaker: genuine. Shoes: genuine. Air Fryer: likely inflated                                                |
| Collector status | a clear message that nothing has been collected yet                                                         |

### 6. API, valid requests

Open http://127.0.0.1:8000/docs and use "Try it out".

| **Request**                           | **Expected**                             |
| ------------------------------------- | ---------------------------------------- |
| `GET /api/products`                   | 200, 3 products                          |
| `GET /api/products?search=air`        | 200, only Demo Air Fryer (fake discount) |
| `GET /api/products/1`                 | 200                                      |
| `GET /api/products/1/history?days=30` | 200                                      |
| `GET /api/products/3/trust-score`     | 200, label `likely_inflated`             |
| `GET /api/scrape-runs`                | 200, `[]` (no runs yet)                  |

### 7. API, bad input

| **Request**                                  | **Expected** |
| -------------------------------------------- | ------------ |
| `GET /api/products/999999`                   | 404          |
| `GET /api/products/1/history?days=0`         | 422          |
| `GET /api/products?search=` + 201 characters | 422          |

### 8. One real collector cycle

Check first that nobody else on the team is running the collector against the
site right now. Open a **second** terminal in the same folder:

```powershell
.\.venv\Scripts\Activate.ps1
python -m backend.scheduler.jobs
```

Wait until the log shows the first cycle has finished, then press Ctrl+C.

**Expected:** the log shows the page being fetched and the number of products
seen. Write down that number and the time.

### 9. Was it saved?

```powershell
python -m backend.devtools.check_db
```

Then refresh http://127.0.0.1:8000/api/scrape-runs and the dashboard.

**Expected:**

- The newest run is `success`.
- Its `products_seen` is the number from step 8.
- `check_db` shows the same number of snapshots for that run.
- The dashboard's collector status now shows this run.

Write down the run id, status, `products_seen`, snapshot count and the health
status that `check_db` prints.

### 10. Automated checks

```powershell
ruff check .
ruff format --check .
pytest -q
```

**Expected:** all three pass. Write down the last line of each.

### 11. Failures

Open a GitHub issue for every `FAIL`: steps to reproduce, expected, actual, and
the commit hash. Link each issue in the table. If nothing failed, write
`No failures found`.

## v0.1 results

- **Date:** 2026-10-16
- **Tested by:** @mathango
- **Commit (`git rev-parse HEAD`):** `a420a5324f955807db59fb63e79a6e1977af59f8`
- **Windows version:** Windows 11 Pro
- **Python version:** Python 3.14.7

| **Step**                 | **Result** | **What I saw**                                                                                                                                                               |
| ------------------------ | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1. Fresh clone           | PASS       | Clone succeeded, on `dev`, working tree clean. Commit `a420a5324f955807db59fb63e79a6e1977af59f8`.                                                                            |
| 2. Python setup          | PASS       | `(.venv)` prompt, `pip install` finished without errors. Python 3.14.7.                                                                                                      |
| 3. Seed fake data        | PASS       | `Seeded 3 fake products.` `check_db`: Total products: 3, CHECK REQUIRED (no finished scrape run found).                                                                      |
| 4. Start the app         | PASS       | `/api/health` returned HTTP 200 with `{"status":"ok"}`.                                                                                                                      |
| 5. Dashboard             | PASS       | Grid showed 3 demo products; search `air` returned only Demo Air Fryer; search `zzzz` showed "No products match your search."; product detail with price chart; Trust Score labels as expected; collector status showed "nothing collected yet". |
| 6. API, valid requests   | PASS       | `/api/products` 200 (3 products); `?search=air` 200 (only Air Fryer); `/api/products/1` 200; `/history?days=30` 200; `/api/products/3/trust-score` 200 `likely_inflated`; `/api/scrape-runs` 200 `[]`. |
| 7. API, bad input        | PASS       | `/api/products/999999` 404; `/history?days=0` 422; 201-char search 422.                                                                                                      |
| 8. Collector cycle       | PASS       | Books to Scrape fetched HTTP 200, `robots.txt` 404 (warning logged, collector continued), 3-second delay observed, 20 products seen. Collector stopped `2026-10-16 17:21:43`. |
| 9. Saved to the database | PASS       | run 1, success, products_seen 20, 20 snapshots. Database Health status: Healthy. Dashboard collector status: "Completed successfully", products seen 20, last collected `10/16/2026, 5:19:22 PM`. Total products in database: 23 (3 products without a snapshot in this run). No duplicate product names. |
| 10. ruff and pytest      | PASS       | `All checks passed!` / all files already formatted / 270 passed.                                                                                                             |
| 11. Failures             | COMPLETE   | No failures found.                                                                                                                                                           |


