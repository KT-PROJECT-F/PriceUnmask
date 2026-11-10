## What it does

The scraper fetches listing pages from the configured target, checking robots.txt before each page.
It uses our configured User-Agent, a polite delay, a timeout, and bounded retries for temporary failures.
It parses products and follows same-site next-page links up to `SCRAPE_MAX_PAGES`.
It saves each page’s raw HTML snapshot and returns product records; the collector, not the scraper, writes to the database.
`scrape()` selects a `SourceAdapter` by URL and keeps fetching, snapshots, deduplication, and page limits shared across adapters.

## Source adapters

- `SourceAdapter` is an abstract base class. A new adapter subclasses it and implements
  `supports(url)`, `parse_listing(html, base_url)`, and
  `parse_next_page_url(html, base_url)`. Python prevents instantiating an adapter that omits an
  abstract method. This and the unsupported-URL behavior are scraper contract changes in this PR;
  `ScrapedProduct.source` itself already exists on `dev` from #236.
- The demo adapter requires pagination links to stay on the same listing path, preventing a
  next-page link from sending collection to another category. Books to Scrape pagination is not
  restricted to the same path because its valid next pages use paths such as
  `/catalogue/page-2.html`; both adapters still require the same host and a valid HTTP(S) URL.
- If a demo card has no usable currency metadata, it is retained with the existing USD fallback
  and a warning is logged so the assumption is visible.
- **Books to Scrape** remains a supported practice adapter. Its existing public parsing functions
  and pagination behavior are retained. Products leave `source` unset, so the scheduler's
  existing `SOURCE_KEY` remains the single place defining `books-toscrape`.
- **Croma** retains the existing directly configured product-detail parser as an adapter. Its
  terms were assessed as unclear in [shop-evaluation.md](../shop-evaluation.md); do not use it for
  unattended collection unless permission is established.
- **Web Scraper's static e-commerce test site** has a parser adapter (`webscraper-demo`) used only
  with controlled local HTML tests for now. The `User-agent: *` rules in
  `https://webscraper.io/robots.txt`, retrieved 10 November 2026, do not disallow the proposed
  e-commerce listing, pagination, or product paths. However, the site's
  [test-sites page](https://webscraper.io/test-sites) describes them as training sites for learning
  the Web Scraper extension and does not establish permission for PriceUnmask collection or
  retaining a real-page fixture. Do not add a real-page fixture or enable live collection until
  the reviewer or site owner confirms that use is permitted; see
  [shop-evaluation.md](../shop-evaluation.md).
- Every page still passes through the common fetcher, including its robots.txt check, User-Agent,
  delay, timeout, and retry policy.
- `ScrapedProduct.source` is already an optional field in the current contract. Croma and
  webscraper-demo set it; Books leaves it unset, using the scheduler's existing fallback.
- Unsupported or empty target URLs are rejected before any request with `ValueError`; the
  scheduler catches this and records the scrape run as failed. This is intentional: the scraper
  now only fetches URLs explicitly supported by a registered adapter.

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

Tests replace `requests.get` with fake responses, so they check scraper behavior without sending requests to a real website. Saved Books to Scrape fixtures and controlled Web Scraper card HTML test parsing offline; no Web Scraper listing fixture is included pending a decision on whether the site's training-use statement permits retaining its HTML in this repository.
- `test_disallowed_url_never_requests_the_page` proves a robots.txt block prevents the page request ([`test_fetcher.py:284`](../../tests/test_fetcher.py#L284)).
- `test_timeout_is_retried` proves timeouts get bounded retries ([`test_fetcher.py:241`](../../tests/test_fetcher.py#L241)).
- `test_scrape_saves_raw_html` proves fetched HTML is saved as a snapshot ([`test_fetcher.py:375`](../../tests/test_fetcher.py#L375)).

## Known limits and what we would do next

Books to Scrape uses fixed sample prices. The Web Scraper demo adapter is not approved for live
collection: its reviewed robots.txt does not disallow the proposed path, but the terms page does
not establish permission for PriceUnmask collection or retaining a fixture. These adapters
exercise the collection pipeline but do not demonstrate real market trends or validate price-change
alerts. Next, obtain a reviewer/site-owner decision or evaluate another practice shop whose
robots.txt and terms allow the intended use, then review the parsing assumptions with Mathan.