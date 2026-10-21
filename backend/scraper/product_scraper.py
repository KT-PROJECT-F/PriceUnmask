"""Scraper. Owners: Scraper track (2 people: parsing + robustness).

Contract: `scrape(url)` returns a list of ScrapedProduct and NEVER touches
the database.

Keeping the scraper pure (HTML in, dataclasses out) means it can be
unit-tested against saved HTML files with zero network calls.
"""

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import sleep
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from backend.config import settings

FETCH_TIMEOUT_SECONDS = 10
SNAPSHOT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "snapshots"
MAX_RETRIES = 2
BACKOFF_SECONDS = 1
RETRY_STATUSES = {500, 502, 503, 504}

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScrapedProduct:
    external_id: str
    name: str
    url: str
    current_price_minor: int
    original_price_minor: int | None
    in_stock: bool | None
    currency: str
    scraped_at: datetime


def parse_price_to_minor(text: str) -> int | None:
    """Convert a supported price string into minor currency units."""
    if not isinstance(text, str):
        return None

    value = text.strip()
    if not value:
        return None

    value = re.sub(
        r"^(?:Rs\.?|[\u00a3\u20b9])\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = value.replace(",", "").strip()

    match = re.fullmatch(r"(\d+)(?:\.(\d{1,2}))?", value)
    if not match:
        return None

    whole = match.group(1)
    decimal = (match.group(2) or "").ljust(2, "0")

    return int(whole) * 100 + int(decimal)


def parse_listing(html: str, base_url: str) -> list[ScrapedProduct]:
    """Parse one listing page and skip invalid product cards."""
    soup = BeautifulSoup(html, "html.parser")
    products: list[ScrapedProduct] = []
    scraped_at = datetime.now(UTC)
    cards = soup.select("article.product_pod")

    for card in cards:
        link = card.select_one("h3 a")
        price_element = card.select_one(".price_color")
        availability_element = card.select_one(".availability")

        if not link or not link.get("href"):
            logger.warning("Skipping product card with no product link")
            continue

        name = link.get("title") or link.get_text(strip=True)

        if not name:
            logger.warning("Skipping product card with no name")
            continue

        relative_url = link.get("href")

        if not price_element:
            logger.warning("Skipping product card with no price: %s", name)
            continue

        url = urljoin(base_url, relative_url)
        price_text = price_element.get_text(strip=True)
        price_minor = parse_price_to_minor(price_text)

        if price_minor is None:
            logger.warning(
                "Skipping product card with unreadable price: %s",
                name,
            )
            continue

        original_price_minor = None
        original_price_element = card.select_one("del, .old-price")

        if original_price_element:
            original_price_minor = parse_price_to_minor(original_price_element.get_text(strip=True))

            if original_price_minor is not None and original_price_minor <= price_minor:
                logger.warning(
                    "Ignoring old price that is not above the price: %s",
                    name,
                )
                original_price_minor = None

        url_path = url.rstrip("/").split("/")
        filename = url_path[-1]
        slug = url_path[-2] if filename == "index.html" and len(url_path) >= 2 else filename
        external_id = slug.rsplit("_", 1)[0]

        currency = "INR" if ("\u20b9" in price_text or "Rs" in price_text) else "GBP"

        in_stock = None

        if availability_element:
            availability = availability_element.get_text(" ", strip=True)
            in_stock = "In stock" in availability

        products.append(
            ScrapedProduct(
                external_id=external_id,
                name=name,
                url=url,
                current_price_minor=price_minor,
                original_price_minor=original_price_minor,
                in_stock=in_stock,
                currency=currency,
                scraped_at=scraped_at,
            )
        )

    if cards and not products:
        logger.error(
            "Skipped all %d product cards; the page layout may have changed",
            len(cards),
        )

    return products


def parse_next_page_url(html: str, current_url: str) -> str | None:
    """Return the next listing page URL, or None if no next page exists."""
    soup = BeautifulSoup(html, "html.parser")

    next_link = soup.select_one("li.next a[href]")

    if next_link is None:
        next_link = soup.select_one('a[rel="next"][href]')

    if next_link is None:
        return None

    next_url = urljoin(current_url, next_link["href"])

    current = urlparse(current_url)
    next_page = urlparse(next_url)

    # Do not follow pagination links to another host.
    if next_page.scheme not in {"http", "https"} or next_page.netloc != current.netloc:
        logger.warning(
            "Ignoring pagination link outside the current host: %s",
            next_url,
        )
        return None

    # Avoid repeatedly fetching the same page.
    if next_url == current_url:
        return None

    return next_url


def _robots_allows(url: str, headers: dict[str, str]) -> bool:
    """Return whether robots.txt allows fetching the requested URL."""
    robots_url = urljoin(url, "/robots.txt")
    logger.info("Checking robots.txt: %s", robots_url)

    try:
        response = requests.get(
            robots_url,
            headers=headers,
            timeout=FETCH_TIMEOUT_SECONDS,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not fetch robots.txt for {url}: {exc}") from exc

    if 300 <= response.status_code < 400:
        raise RuntimeError(f"robots.txt redirected (HTTP {response.status_code}) for {url}")

    if response.status_code == 404:
        logger.warning(
            "robots.txt returned 404; allowing fetch of %s",
            url,
        )
        return True

    if response.status_code >= 400:
        raise RuntimeError(f"robots.txt returned HTTP {response.status_code} for {url}")

    parser = RobotFileParser()
    parser.parse(response.text.splitlines())

    return parser.can_fetch(settings.scrape_user_agent, url)


def fetch_html(url: str) -> str:
    """Fetch HTML with robots checks, timeouts, retries, and backoff."""
    headers = {"User-Agent": settings.scrape_user_agent}
    logger.info("Using User-Agent: %s", headers["User-Agent"])

    if not _robots_allows(url, headers):
        logger.warning("robots.txt disallows fetching %s", url)
        raise RuntimeError(f"robots.txt disallows fetching {url}")

    if settings.scrape_delay_seconds > 0:
        logger.info(
            "Waiting %.2f seconds before fetching %s",
            settings.scrape_delay_seconds,
            url,
        )
        sleep(settings.scrape_delay_seconds)

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=FETCH_TIMEOUT_SECONDS,
                allow_redirects=False,
            )
        except (requests.Timeout, requests.ConnectionError):
            if attempt == MAX_RETRIES:
                raise

            wait_seconds = BACKOFF_SECONDS * (2**attempt)
            logger.warning(
                "Request failed; retry %s of %s in %s seconds",
                attempt + 1,
                MAX_RETRIES,
                wait_seconds,
            )
            sleep(wait_seconds)
            continue

        if 300 <= response.status_code < 400:
            location = response.headers.get("Location", "no Location header")
            raise RuntimeError(
                f"Redirect not followed: {url} -> {location} (HTTP {response.status_code})"
            )

        if response.status_code >= 400:
            if response.status_code not in RETRY_STATUSES:
                raise RuntimeError(f"Failed to fetch {url}: HTTP {response.status_code}")

            if attempt == MAX_RETRIES:
                raise RuntimeError(f"Failed to fetch {url}: HTTP {response.status_code}")

            wait_seconds = BACKOFF_SECONDS * (2**attempt)
            logger.warning(
                "HTTP %s; retry %s of %s in %s seconds",
                response.status_code,
                attempt + 1,
                MAX_RETRIES,
                wait_seconds,
            )
            sleep(wait_seconds)
            continue

        content_type = response.headers.get("Content-Type", "")
        media_type = content_type.split(";")[0].strip().lower()

        if media_type not in {"text/html", "application/xhtml+xml"}:
            raise RuntimeError(f"Expected HTML from {url}, got {content_type or 'no Content-Type'}")

        logger.info("Fetched %s: HTTP %s", url, response.status_code)

        if "charset" not in content_type.lower():
            response.encoding = response.apparent_encoding

        return response.text

    raise RuntimeError(f"Failed to fetch {url} after {MAX_RETRIES + 1} attempts")


def scrape(url: str) -> list[ScrapedProduct]:
    """Fetch, save raw HTML, parse, and return products from multiple pages.

    Collects up to settings.scrape_max_pages listing pages.
    Saves each page as a separate HTML snapshot and removes duplicate
    products when their external IDs are available.

    Any fetch failure is raised to the caller.
    """
    max_pages = max(1, int(settings.scrape_max_pages))

    current_url: str | None = url
    visited_urls: set[str] = set()
    seen_product_ids: set[str] = set()
    all_products: list[ScrapedProduct] = []

    for page_number in range(1, max_pages + 1):
        if current_url is None:
            break

        if current_url in visited_urls:
            logger.warning(
                "Stopping pagination because the URL was already visited: %s",
                current_url,
            )
            break

        visited_urls.add(current_url)

        logger.info(
            "Scraping listing page %s of %s: %s",
            page_number,
            max_pages,
            current_url,
        )

        html = fetch_html(current_url)

        # Preserve the original snapshot filename format for page 1.
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

        if page_number == 1:
            snapshot_path = SNAPSHOT_DIR / f"{timestamp}.html"
        else:
            snapshot_path = SNAPSHOT_DIR / f"{timestamp}_page{page_number}.html"

        try:
            SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_text(html, encoding="utf-8")
        except OSError:
            logger.exception(
                "Could not save raw HTML snapshot to %s",
                snapshot_path,
            )

        page_products = parse_listing(html, current_url)

        for product in page_products:
            # Keep compatibility with existing tests and parsers that return
            # objects without an external_id attribute.
            external_id = getattr(product, "external_id", None)

            if external_id is not None:
                if external_id in seen_product_ids:
                    logger.info(
                        "Skipping duplicate product ID: %s",
                        external_id,
                    )
                    continue

                seen_product_ids.add(external_id)

            all_products.append(product)

        logger.info(
            "Collected %s products from page %s; total products: %s",
            len(page_products),
            page_number,
            len(all_products),
        )

        if page_number == max_pages:
            break

        current_url = parse_next_page_url(html, current_url)

        if current_url is None:
            logger.info("No next listing page found; collection complete")
            break

    logger.info(
        "Scraping complete: %s products collected across %s pages",
        len(all_products),
        len(visited_urls),
    )

    return all_products
