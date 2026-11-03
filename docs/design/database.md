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

The database tests cover product persistence, price history, timestamps, search behaviour, stale-run cleanup, and collector/API database access.

Important tests include:

- `test_upsert_same_product_twice_gives_one_product_two_snapshots` verifies product reuse and history preservation.
- `test_read_functions_return_aware_utc_timestamps` verifies returned timestamps are timezone-aware UTC.
- `test_mark_one_stale_run_failed` verifies stale-run cleanup.
- `test_list_products_search_percent_matches_literal_character` verifies literal `%` search.
- `test_api_can_read_while_collector_write_is_uncommitted` verifies that the API can read committed data while the collector has an uncommitted write, and can see the new product after the collector commits.

The concurrency integration test uses a temporary file-backed SQLite database with WAL enabled. It exercises the actual collector write path while the API product-list endpoint reads committed data. It verifies reader/writer concurrency, not simultaneous independent writers.

## Database choice: SQLite or PostgreSQL

**Decision: Keep SQLite with WAL for the current application. Do not migrate to PostgreSQL yet.**

### Why we chose SQLite

- The existing application already uses SQLite and SQLAlchemy.
- WAL allows API readers to continue reading committed data while a collector write is in progress.
- The new file-backed concurrency integration test verifies this reader/writer behaviour.
- The existing schema supports multiple data sources through the unique `(source, external_id)` product constraint.
- Adding another source does not by itself require a database migration.

### Limitations

SQLite allows only one active writer at a time. WAL improves reader/writer concurrency, but it does not provide unrestricted concurrent writes.

Issue #223 identifies the need for another source with changing prices and discount claims because Books to Scrape did not provide useful price changes or original-price values during the observed collection period.

However, the issue description does not establish the new source's actual product count, collection frequency, or resulting database growth. These values must be measured after the new source is integrated.

The current demo database is not representative production workload evidence and should not be used to justify a database migration.

### When we would consider PostgreSQL

We should evaluate PostgreSQL if measurements show any of the following:

- Frequent SQLite database-locked or busy errors during normal collection.
- Sustained write contention as multiple sources are collected.
- API read latency or collector completion time becomes unacceptable.
- Deployment requires multiple application instances or independent collector workers writing to the same database.

Before migrating, measure product counts by source, snapshots collected per day, database size, write failures, transaction duration, and API response latency during collection.

### Future evaluation

The decision to retain SQLite is provisional until the new source's
actual collection volume and database growth have been measured.
Once Issue #223 is integrated, collect workload metrics before
reassessing whether PostgreSQL is necessary.
Keep SQLite with WAL while it meets the application's measured workload. Revisit PostgreSQL when actual collection metrics demonstrate that SQLite's single-writer limitation or deployment requirements are becoming a problem.
