# Database Design

## What it does

The database stores products, scrape runs, and price snapshots. Products keep the latest product details, while snapshots preserve observed prices over time. Scrape runs record when collection starts, finishes, or fails. SQLAlchemy models define the data structure, and CRUD functions provide the main database access methods.

See [ARCHITECTURE.md](../ARCHITECTURE.md) for the overall system architecture.

## Decisions

1. **Integer prices:** Prices use integer minor units instead of floats to avoid floating-point rounding errors. For example, ₹1,299.50 is stored as `129950` paise. Decimal floats were not chosen because they cannot represent many decimal values exactly. See [models.py](../../backend/db/models.py).

2. **UTC timestamps:** `UTCDateTime` converts aware datetimes to UTC before storage and returns aware UTC datetimes when reading. Naive datetimes are rejected because their timezone is unknown. This is more consistent than storing local times from different machines. See [models.py](../../backend/db/models.py).

3. **Product identity and price history:** A product is unique by `(source, external_id)`, not its name, because names can change or be duplicated. Each observation creates a new `PriceSnapshot` instead of overwriting an old price. Updating product details while retaining snapshots preserves historical comparisons. See [models.py](../../backend/db/models.py) and [crud.py](../../backend/db/crud.py).

4. **Centralised database access and literal search:** CRUD functions keep query logic in one place. Product search escapes `%` and `_` so they match literal characters instead of acting as SQL `LIKE` wildcards. The alternative—unescaped search—can return misleading matches. See [crud.py](../../backend/db/crud.py).

## How it fails, and what happens then

A scrape run starts with `running` status. If it remains running beyond the stale-run threshold, `mark_stale_runs_failed` marks it failed, records a finish time, and stores an error message. Fresh runs and already completed runs are left unchanged. `has_running_scrape_run` checks whether any run still has running status. Snapshots remain unchanged when a run is marked stale.

## How it is tested

`tests/test_crud.py` checks the main database behaviour:

- `test_upsert_same_product_twice_gives_one_product_two_snapshots` verifies product reuse and history preservation.
- `test_read_functions_return_aware_utc_timestamps` verifies returned timestamps are timezone-aware UTC.
- `test_mark_one_stale_run_failed` verifies stale-run cleanup.
- `test_list_products_search_percent_matches_literal_character` verifies literal `%` search.

## Known limits and what we would do next

The current design uses SQLite and SQLAlchemy. SQLite write concurrency and database growth may become limitations as collection volume increases. Next, we could add stronger integration tests for concurrent writes and evaluate a server database if workload demands it.