# PriceUnmask architecture

Status: v1, agreed at kickoff. Changes to anything in sections 3 to 6 need a PR the mentor approves.

## 1. What we are building

A small system that runs by itself: every few hours it scrapes prices from one shop,
stores every observation, and scores each "discount" for how real it is.

```
  [ shop website ]
        |  HTTP (every 4h, polite: robots.txt, delay, our User-Agent)
        v
  scraper/  --- list[ScrapedProduct] --->  scheduler/jobs.py  --- crud.py --->  SQLite
  (pure: HTML in, dataclasses out)         (runs forever,                     (products,
                                            logs every run)                    price_snapshots,
                                                                               scrape_runs)
                                                                                  |
  frontend/ (HTML/JS/Chart.js) <--- JSON --- main.py (FastAPI, /api) <--- crud.py + analysis/
                                                                     (trust_score, anomaly_model)
```

## 2. Key decisions (and why)

| Decision | Why |
|---|---|
| Prices stored as **integer minor units** (paise) | Floats cannot store most decimals exactly. |
| Timestamps are **UTC, timezone-aware** | Scheduler, DB and browser can be in different zones. |
| `price_snapshots` is **append-only** | History is the product. Never edit the past. |
| `scrape_runs` table | Proves the system ran unattended; makes failures visible (rubric: system thinking). |
| Scraper never touches the DB | Pure functions are testable against saved HTML, no network in tests. |
| All DB access goes through `crud.py` | One place to change queries; no SQL scattered across modules. |
| Frontend served by FastAPI at `/`, API at `/api` | One process, no CORS, one command to run. |
| SQLite in WAL mode | Scheduler writes while API reads without locking errors. |
| `insufficient_data` is a real Trust Score label | Honest about sparse early data (rubric: ML reasoning). |
| One **collector** machine owns the real DB | Real history must accumulate in ONE place. See section 7. |

## 3. Data model (backend/db/models.py)

- **products**: id, source, external_id (unique per source), name, url, currency, is_active, created_at, last_seen_at
- **price_snapshots**: id, product_id (FK), scrape_run_id (FK), scraped_at (indexed with product_id), current_price_minor, original_price_minor (nullable), in_stock (nullable)
- **scrape_runs**: id, started_at, finished_at, status (running | success | partial | failed), products_seen, error_message

## 4. Module contracts

Stubs with exact signatures already exist in the code. Implement the body; do not change the
signature without a PR tagged `contract-change` that the affected owners review.

| Module | Public contract | Depends on |
|---|---|---|
| `scraper/product_scraper.py` | `ScrapedProduct`, `parse_price_to_minor`, `parse_listing`, `fetch_html`, `scrape` | nothing |
| `db/crud.py` | `start_scrape_run`, `finish_scrape_run`, `upsert_product_and_snapshot`, `list_products`, `get_product`, `get_history`, `list_scrape_runs` | models |
| `scheduler/jobs.py` | `run_scrape_cycle() -> int`, `build_scheduler()` | scraper, crud |
| `analysis/trust_score.py` | `compute_signals(df)`, `compute_trust_score(df) -> TrustScore` | pandas only |
| `analysis/anomaly_model.py` | `detect_anomalies(df) -> AnomalyResult` | pandas, sklearn |
| `schemas.py` + `main.py` | endpoints in section 5 | crud, analysis |
| `frontend/` | consumes section 5 only | API |

Analysis functions take a **pandas DataFrame**, not ORM objects, with columns
`scraped_at, current_price_minor, original_price_minor`, oldest first. The API layer converts.

## 5. API (all under /api)

| Method | Path | Returns | Errors |
|---|---|---|---|
| GET | `/api/health` | `{"status":"ok"}` | |
| GET | `/api/products?search=` | `list[ProductOut]` | |
| GET | `/api/products/{id}` | `ProductOut` | 404 |
| GET | `/api/products/{id}/history?days=` | `HistoryOut` | 404 |
| GET | `/api/products/{id}/trust-score` | `TrustScoreOut` | 404 |
| GET | `/api/scrape-runs` | `list[ScrapeRunOut]` | |
| POST | `/api/scrape/run` | `ScrapeRunOut` (202) | 409 if a run is already in progress |

## 6. Trust Score signals (each must be explainable in one sentence)

| Signal | Plain-English meaning | Fake-discount pattern |
|---|---|---|
| Spike before discount | Price went up shortly before the sale started | Hike then "slash" to near the old price |
| Real discount vs median | Current price compared to the typical recent price | Claimed 70% off, real saving 5% |
| Claimed vs real discount gap | Strikethrough % minus real % | Big gap means the "original" price is fiction |
| % above lowest ever | How far today is from the best price we saw | "Deal" is above what it cost last week |
| Volatility | How much the price normally moves | High volatility makes any single "deal" less meaningful |

Score 0 to 100. `>= 70` genuine, `40 to 69` uncertain, `< 40` likely_inflated,
fewer than 6 snapshots `insufficient_data`. `reasons` lists the sentences shown to the user.

## 7. Where real data comes from

- One **collector** (mentor's always-on machine or a free-tier VM) runs
  `python -m backend.scheduler.jobs` against the real `data/priceunmask.db`.
- Start it the day the scraper and crud land on `dev`. Every day it is not running is
  history we will never get back.
- Mentor exports a DB copy to the team every few days for analysis and frontend work.
- Everyone else develops against `python -m backend.devtools.seed_fake_data`.

## 8. Scraping rules (non-negotiable)

- One public site with no login wall. Check its `robots.txt` and Terms before choosing it.
- Identify ourselves via User-Agent, wait `SCRAPE_DELAY_SECONDS` between requests,
  no more than one listing page per run per category.
- If the site blocks us, we stop and pick another site; we do not rotate proxies or fake browsers.
- Tests never hit the network. Save real HTML to `data/snapshots/sample_*.html` and parse that.

## 9. Team tracks (8 people)

| # | Track | Owns | First deliverable |
|---|---|---|---|
| 1 | Scraper A: parsing | `parse_listing`, `parse_price_to_minor`, sample HTML | Parser + tests on saved HTML |
| 2 | Scraper B: fetching | `fetch_html`, `scrape`, robots.txt, retries, snapshot files | Polite fetcher with retries |
| 3 | Database | `crud.py`, test fixtures, DB export script | All crud functions + tests |
| 4 | Scheduler | `jobs.py`, run logging, failure handling | Collector running unattended |
| 5 | Analysis: rules | `trust_score.py` | Scores the 3 seeded products correctly |
| 6 | Analysis: ML | `anomaly_model.py`, pandas feature helpers | z-score pass, then IsolationForest |
| 7 | API | `schemas.py`, `main.py` routes, API tests | All endpoints on fake data |
| 8 | Frontend | `frontend/*` | Grid + detail chart on mock JSON, then live API |

Review buddies (review each other's PRs before the mentor): 1 and 2, 3 and 4, 5 and 6, 7 and 8.

## 10. Milestones (today: Sun 27 Sept; submission: Sat 31 Oct)

| Milestone | Dates | Definition of done | Release |
|---|---|---|---|
| M0 Setup | 28 to 30 Sept | Everyone cloned, ran tests, merged one small PR into `dev` | |
| M1 Collecting | by Sun 4 Oct | Scraper + crud + scheduler on `dev`; collector running | |
| M2 Features | 5 to 14 Oct | Trust score, anomaly, all endpoints, grid + chart, each on fake data | `dev -> main` v0.1 |
| M3 Integration | 15 to 24 Oct | Everything on real collected data; error handling pass | `dev -> main` v0.2 |
| M4 Hardening | 25 to 31 Oct | Tests, README, notes.md, demo | `dev -> main` v1.0 |
