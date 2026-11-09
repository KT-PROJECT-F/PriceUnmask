## What it does

The scraper fetches listing pages from the configured target, checking robots.txt before each page.
It uses our configured User-Agent, a polite delay, a timeout, and bounded retries for temporary failures.
It parses products and follows same-site next-page links up to `SCRAPE_MAX_PAGES`.
It saves each page’s raw HTML snapshot and returns product records; the collector, not the scraper, writes to the database.
`scrape()` selects a `SourceAdapter` by URL and keeps fetching, snapshots, deduplication, and page limits shared across adapters.

## Source adapters

- **Books to Scrape** remains a supported practice adapter. Its existing public parsing functions
  and pagination behavior are retained.
- **Web Scraper's static e-commerce test site** is the second adapter (`webscraper-demo`). Its
  product cards use USD prices and stable product IDs from product URLs. The site describes the
  catalog as a training site and says its items are not for sale; the adapter is intended for this
  practice catalog, not the vendor's commercial pages.
- Every page still passes through the common fetcher, including its robots.txt check, User-Agent,
  delay, timeout, and retry policy.
- `ScrapedProduct.source` is optional so existing construction remains compatible. Adapters set it
  when the source differs from the scheduler's existing Books fallback; this field is a contract
  change and requires the `contract-change` PR label.

## Decisions

- **Keep fetching and parsing out of the database layer.** The scraper returns product records; the collector saves them. This separation keeps scraping testable without a database ([`product_scraper.py:5`](../../backend/scraper/product_scraper.py#L5), [`jobs.py:102`](../../backend/scheduler/jobs.py#L102)).
- **Check robots.txt, identify our bot, and wait between requests.** This makes the scraper’s requests identifiable and more considerate of the site. We do not fetch first and check permission later ([`product_scraper.py:246`](../../backend/scraper/product_scraper.py#L246), [`product_scraper.py:278`](../../backend/scraper/product_scraper.py#L278)).
- **Do not follow redirects.** A redirect could send a request somewhere we did not intend to scrape, so we stop and report it rather than silently fetching the destination ([`product_scraper.py:210`](../../backend/scraper/product_scraper.py#L210), [`product_scraper.py:318`](../../backend/scraper/product_scraper.py#L318)).
- **Retry temporary failures, not every error.** Timeouts and selected server errors get bounded retries; a 404 is treated as a final response because repeating a missing-page request is unlikely to help ([`product_scraper.py:197`](../../backend/scraper/product_scraper.py#L197), [`product_scraper.py:263`](../../backend/scraper/product_scraper.py#L263)).

## How it fails, and what happens then

| What goes wrong | What the scraper does | What the collector records |
|---|---|---|
| robots.txt blocks the page or returns an error other than 404 | Stops before fetching the page; a robots.txt 404 allows the page request | Failed run with the error, except for a robots.txt 404 |
| Page request times out | Retries, then stops if all attempts fail | Failed run with the error |
| Page returns 404 | Does not retry; stops | Failed run with the HTTP error |
| Page redirects | Rejects the redirect without following it | Failed run with the redirect error |
| Page layout changes | Logs an error if it finds product cards but cannot parse any products | May record a successful run with zero or fewer products; layout changes are not automatically classified as failures |

## How it is tested

Tests replace `requests.get` with fake responses, so they check scraper behavior without sending requests to a real website. Saved HTML fixtures test parsing against known pages.
- `test_disallowed_url_never_requests_the_page` proves a robots.txt block prevents the page request ([`test_fetcher.py:284`](../../tests/test_fetcher.py#L284)).
- `test_timeout_is_retried` proves timeouts get bounded retries ([`test_fetcher.py:241`](../../tests/test_fetcher.py#L241)).
- `test_scrape_saves_raw_html` proves fetched HTML is saved as a snapshot ([`test_fetcher.py:375`](../../tests/test_fetcher.py#L375)).

## Known limits and what we would do next

Books to Scrape uses fixed sample prices, and Web Scraper's catalog is a training site whose
items are not for sale. These adapters exercise the collection pipeline but do not demonstrate
real market trends or validate price-change alerts. Next, evaluate a production shop whose terms
permit collection and whose prices change, then review the parsing assumptions with Mathan.