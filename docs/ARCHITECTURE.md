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
| `insufficient_data` and `no_discount` are Trust Score labels | Honest about sparse early data; distinguishes insufficient history from no valid discount claim. |
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
| `scraper/product_scraper.py` | `ScrapedProduct`, `SourceAdapter`, `parse_price_to_minor`, `parse_listing`, `fetch_html`, `scrape` | nothing |
| `db/crud.py` | `start_scrape_run`, `finish_scrape_run`, `upsert_product_and_snapshot`, `list_products`, `get_product`, `get_history`, `list_scrape_runs`, `get_product_trends` | models |
| `scheduler/jobs.py` | `run_scrape_cycle() -> int`, `build_scheduler()` | scraper, crud |
| `analysis/trust_score.py` | `compute_signals(df)`, `compute_trust_score(df) -> TrustScore` | pandas only |
| `analysis/anomaly_model.py` | `detect_anomalies(df) -> AnomalyResult` | pandas, sklearn |
| `analysis/price_history_utils.py` | `get_valid_price_history`, `compare_first_and_latest_prices` | pandas |
| `analysis/price_drop.py` | `detect_price_drop(history) -> PriceDropResult` | price_history_utils |
| `analysis/price_trend.py` | `calculate_price_trend` | price_history_utils |
| `schemas.py` + `main.py` | endpoints in section 5 | crud, analysis |
| `frontend/` | consumes section 5 only | API |

Analysis functions take a **pandas DataFrame**, not ORM objects, with columns
`scraped_at, current_price_minor, original_price_minor`, oldest first. The API layer converts.

`ScrapedProduct.source` is an optional field already present on `dev` from #236; this PR does not
change the product contract. This PR adds the scraper's `SourceAdapter` extension contract and
changes `scrape(url)` to raise `ValueError` before fetching when no adapter supports the URL; these
scraper API changes require the `contract-change` label and scraper-owner review. `SourceAdapter`
is an abstract base class: each adapter must implement `supports`, `parse_listing`, and
`parse_next_page_url`, and an incomplete adapter cannot be instantiated. Adapters that need a
non-default source set it on parsed products; Books to Scrape leaves it unset so the scheduler's
existing `SOURCE_KEY` remains the single source of its `books-toscrape` key. The source adapter is
selected from the URL inside `scrape()`, so adding a site does not require per-site changes to
scheduler or database code.

## 5. API (all under /api)

| Method | Endpoint | Success response | Errors |
|---|---|---|---|
| GET | `/api/health` | `{"status":"ok"}` | - |
| GET | `/api/products?search=` | `list[ProductOut]` | 422 `VALIDATION_ERROR` |
| GET | `/api/products/{id}` | `ProductOut` | 404 `PRODUCT_NOT_FOUND`; 422 `VALIDATION_ERROR` |
| GET | `/api/products/{id}/history?days=` | `HistoryOut` | 404 `PRODUCT_NOT_FOUND`; 422 `VALIDATION_ERROR` |
| GET | `/api/products/{id}/trust-score` | `TrustScoreOut` | 404 `PRODUCT_NOT_FOUND`; 422 `VALIDATION_ERROR` |
| GET | `/api/products/{id}/price-drop` | `PriceDropOut` | 404 `PRODUCT_NOT_FOUND`; 422 `VALIDATION_ERROR` |
| GET | `/api/trends/overview?period_days=` | `TrendOverviewOut` | 422 `VALIDATION_ERROR` |
| GET | `/api/scrape-runs` | `list[ScrapeRunOut]` | - |
| POST | `/api/scrape/run` | `ScrapeRunOut` (202 Accepted) | 409 `SCRAPE_ALREADY_RUNNING`; 500 `INTERNAL_SERVER_ERROR` |

All API errors use this response envelope:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": null
  }
}
```
Product list responses include active products only. Product detail requests can return inactive products when requested by ID.

`ProductOut` includes `trust_label`, calculated using the same trust-score logic as the trust-score endpoint and the product's loaded price snapshots.

`GET /api/trends/overview?period_days=` returns trend information for all active
products, including products without sufficient price history.

Trend overview rules:

- `period_days` selects the lookback window beginning at the current UTC time minus
  the requested number of days.
- Only snapshots with a positive `current_price_minor` in the lookback window are
  used for trend calculations.
- The first and latest valid snapshots determine the price change.
- The percentage change is rounded to two decimal places before applying the
  stability threshold.
- Absolute percentage changes below 1% are classified as `stable`.
- Changes at or above 1% are classified as `increasing` or `decreasing`.
- Products with fewer than two valid snapshots are returned with
  `insufficient_history`; their price and change fields are `null`.
- Inactive products are excluded.

Trend directions:

| Direction | Meaning |
|---|---|
| `decreasing` | The latest price is lower than the first price by at least 1%. |
| `increasing` | The latest price is higher than the first price by at least 1%. |
| `stable` | The percentage change is below the 1% stability threshold. |
| `insufficient_history` | Fewer than two valid snapshots are available. |

`products_analyzed` counts all active products included in the overview,
including products with `insufficient_history`.

`products_decreasing`, `products_increasing`, `products_stable`, and
`products_insufficient_history` count products in each direction/status.
These counts add up to `products_analyzed`.

`average_change_percent` is the arithmetic mean of percentage changes for
products with sufficient history. Products with `insufficient_history` are
excluded. It is `null` when no products have sufficient history.

`GET /api/products/{product_id}/price-drop` checks whether the product's latest valid positive price represents a qualifying decrease.

Price-drop calculation rules:

- The latest valid positive price is compared with the reference price at the start of the latest falling stretch.
- Equal consecutive prices remain part of the falling stretch.
- If the latest price has increased, it is compared with the immediately previous valid positive price.
- The drop percentage is rounded to two decimal places.
- A decrease of less than 1% is treated as no qualifying drop. A decrease of at least 1% is treated as a price drop.

Price-drop status meanings:

| Status | Meaning |
|---|---|
| `insufficient_history` | Fewer than two valid positive price snapshots are available. All price and drop fields are `null`. |
| `price_dropped` | The calculated decrease is at least 1%. Drop amount and percentage are calculated using the reference price and latest price. |
| `no_drop` | No qualifying decrease is detected. Drop amount and percentage are `0` and `0.0`, respectively. |

The `PriceDropOut` response includes:

- `product_id`: Product identifier.
- `status`: Price-drop status.
- `previous_price_minor`: Reference price used for the price-drop calculation, in minor units (paise). This is the price at the start of the latest falling stretch, or the immediately previous valid price when the latest price has increased.
- `current_price_minor`: Latest valid price in minor units (paise).
- `drop_amount_minor`: Difference between previous and current prices in minor units.
- `drop_percent`: Percentage decrease, rounded to two decimal places.

A product that does not exist returns 404 `PRODUCT_NOT_FOUND`. Invalid product IDs return 422 `VALIDATION_ERROR`.

`TrustScoreOut` includes the trust score and label. When the result is `no_discount`, the score is `null`.

The trust-score response also includes anomaly information:
- `anomaly_status`: the anomaly analysis status.
- `anomaly_result`: the analysis result when available.
- `anomaly_message`: a human-readable explanation.

Shopper-facing anomaly statuses:

| Status | Meaning |
|---|---|
| `insufficient_history` | Not enough price history to detect unusual price changes. |
| `normal` | Today's price looks normal based on the available history. |
| `unusual` | An unusual price change was detected. Please review the price history before making a purchase. |


`POST /api/scrape/run` closes stale scrape runs before starting a new run. It returns 409 if another scrape run is already in progress. If stale-run cleanup fails, it returns 500 with the standard error envelope.

## 6. Trust Score signals (each must be explainable in one sentence)

| Signal | Plain-English meaning | Fake-discount pattern |
|---|---|---|
| Spike before discount | Price went up shortly before the sale started | Hike then "slash" to near the old price |
| Real discount vs median | Current price compared to the typical recent price | Claimed 70% off, real saving 5% |
| Claimed vs real discount gap | Strikethrough % minus real % | Big gap means the "original" price is fiction |
| % above lowest ever | How far today is from the best price we saw | "Deal" is above what it cost last week |
| Volatility | How much the price normally moves | High volatility makes any single "deal" less meaningful |

Score 0 to 100. `>= 70` genuine, `40 to 69` uncertain, `< 40` likely_inflated.
Fewer than 6 snapshots gives `insufficient_data`. With at least 6 snapshots, if the latest snapshot has no valid discount claim, the label is `no_discount` and `score` is `null`. A valid discount claim requires a positive original price greater than the current price. `reasons` lists the sentences shown to the user.

## 7. Where real data comes from

- One **collector** on Saidivya's machine until 31 Oct demo (see `docs/COLLECTOR.md` - Live collector section) runs `python -m backend.scheduler.jobs` against the real `data/priceunmask.db`.
- Start it the day the scraper and crud land on `dev`. Every day it is not running is history we will never get back.
- Saidivya exports a DB copy via `python -m backend.devtools.export_db` every few days for analysis and frontend work.
- Everyone else develops against `python -m backend.devtools.seed_fake_data`.

## 8. Scraping rules (non-negotiable)

- One public site with no login wall. Check its `robots.txt` and Terms before choosing it.
- Identify ourselves via User-Agent, wait `SCRAPE_DELAY_SECONDS` before every page, and fetch at most `SCRAPE_MAX_PAGES` (default 3) listing pages per run, following the site's own "next" links. Every page goes through `fetch_html`.
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

## 10. Milestones (today: Wed 28 Oct; submission: Sat 31 Oct)

| Milestone | Dates | Definition of done | Release |
|---|---|---|---|
| M0 Setup | 28 Sept to Thu 1 Oct | Everyone cloned, ran tests, merged one small PR into `dev` | |
| M1 Collecting | by Fri 9 Oct | Scraper + crud + scheduler on `dev`; collector running | |
| M2 Features | 1 to 14 Oct | Trust score, anomaly, all endpoints, grid + chart, each on fake data | `dev -> main` v0.1 |
| M3 Integration | 15 to 24 Oct | Everything on real collected data; error handling pass | `dev -> main` v0.2 |
| M4 Hardening | 25 to 31 Oct | Tests, README, design notes, demo | `dev -> main` v1.0 |

Fri 2 Oct (Gandhi Jayanti) is a holiday. Week 1 practice site: https://books.toscrape.com
(prices never change there, so the real shop for history is chosen at the end of Week 1).
