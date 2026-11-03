# Database Design

## What it does

The database stores products, scrape runs, and price snapshots. Products keep the latest product details, while snapshots preserve observed prices over time. Scrape runs record when collection starts, finishes, or fails. SQLAlchemy models define the data structure, and CRUD functions provide the main database access methods.

See [ARCHITECTURE.md](../ARCHITECTURE.md) for the overall system architecture.

## Decisions

### 1. Integer prices

**What we chose:** Prices use integer minor units instead of floats. For example, ₹1,299.50 is stored as `129950` paise.

**Why:** Integer storage avoids floating-point rounding errors during price comparisons.

**What we did not choose:** Decimal prices stored as floating-point values, because many decimal fractions cannot be represented exactly.

**Code references:** [Price storage rule](../../backend/db/models.py#L3-L6) and [PriceSnapshot price columns](../../backend/db/models.py#L137-L149).

### 2. UTC timestamps

**What we chose:** `UTCDateTime` converts timezone-aware datetimes to UTC before storage and returns aware UTC datetimes when reading. Naive datetimes are rejected because their intended timezone is unknown.

**Why:** UTC provides a consistent basis for ordering and comparing observations from different times and machines.

**What we did not choose:** Storing arbitrary local times or accepting naive datetimes, because their intended timezone may be ambiguous.

**Code references:** [UTCDateTime implementation](../../backend/db/models.py#L36-L55), [product timestamps](../../backend/db/models.py#L70-L71), [scrape-run timestamps](../../backend/db/models.py#L85-L86), and [snapshot timestamp](../../backend/db/models.py#L102-L104).

### 3. Product identity and price history

**What we chose:** A product is uniquely identified by `(source, external_id)`. Each observed price is stored in a `PriceSnapshot` instead of overwriting the previous observation.

**Why:** Product names can change or be duplicated. Stable source identifiers help avoid duplicate product records, while snapshots preserve historical price comparisons.

**What we did not choose:** Using the product name as the unique identifier or replacing old snapshots with each new price, because these approaches can lose identity reliability or historical information.

**Code references:** [Product uniqueness constraint](../../backend/db/models.py#L60-L71), [PriceSnapshot model](../../backend/db/models.py#L137-L149), and [product and snapshot write logic](../../backend/db/crud.py#L55-L104).

### 4. Centralized database access

**What we chose:** Database reads and writes are handled through functions in `backend/db/crud.py`. Write functions manage their own commits, while read functions do not commit.

**Why:** Centralizing database operations keeps query and transaction logic in one place.

**What we did not choose:** Scattering database queries and commit operations throughout the scraper and API, because this would duplicate database logic and make changes harder to maintain.

**Code references:** [CRUD module and commit policy](../../backend/db/crud.py#L1-L9) and [product and snapshot writes](../../backend/db/crud.py#L55-L104).

### 5. Literal product search

**What we chose:** Product search escapes `/`, `%`, and `_` before using `ILIKE`, with `/` as the escape character.

**Why:** `%` and `_` have wildcard meanings in SQL pattern matching. Escaping them allows searches to match literal characters in product names.

**What we did not choose:** Passing search text directly into the wildcard pattern, because special characters could produce unintended matches.

**Code references:** [Product search and escaping](../../backend/db/crud.py#L107-L120).

## How it fails, and what happens then

A scrape run starts with `running` status. If the collector stops unexpectedly, its run record may remain in that status.

`has_running_scrape_run` checks whether any run has `running` status; it does not determine whether a run is stale based on its age. Therefore, a run that exceeds the stale-run threshold can still be reported as running until stale-run cleanup executes.

`mark_stale_runs_failed` receives a time threshold, identifies running runs older than that threshold, marks them as failed, records an error message and finish time, commits the changes, and returns the number of runs affected. Fresh runs and already completed runs are not the intended targets of this cleanup. The existing price snapshots are not rewritten merely because a run is marked stale.

The cleanup function must be invoked for this recovery to occur; it is not a background monitor by itself. The configured stale-run threshold defaults to 30 minutes.

**Code references:** [Running-run check](../../backend/db/crud.py#L176-L179) and [stale-run cleanup](../../backend/db/crud.py#L250-L278).

## How it is tested

`tests/test_crud.py` checks important database behaviour:

- `test_upsert_same_product_twice_gives_one_product_two_snapshots` verifies product reuse and history preservation.
- `test_read_functions_return_aware_utc_timestamps` verifies returned timestamps are timezone-aware UTC.
- `test_mark_one_stale_run_failed` verifies stale-run cleanup.
- `test_list_products_search_percent_matches_literal_character` verifies literal `%` search.

## Known limits and what we would do next

The current design uses SQLite and SQLAlchemy. SQLite write concurrency and database growth may become limitations as collection volume increases. Next, we could add stronger integration tests for concurrent writes and evaluate a server database if workload demands it.
