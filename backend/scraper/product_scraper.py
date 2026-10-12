"""Scraper. Owners: Scraper track (2 people: parsing + robustness).

Contract: scrape(url) returns a list of ScrapedProduct and never touches
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
from urllib.parse import urljoin, urlsplit
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
    """Convert a price such as 'Rs. 1,299.50' or '£1,299' to minor units."""
    if not isinstance(text, str):
        return None

    value = text.strip()
    if not value:
        return None

    value = re.sub(
        r"^(?:Rs\.?\s*|[£₹])\s*",
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
    """Parse one listing page.

    Skip and log cards with missing names or prices. A malformed card
    must not cause the entire page to fail.
    """
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

        if not price_element:
            logger.warning("Skipping product card with no price: %s", name)
            continue

        relative_url = link.get("href")
        url = urljoin(base_url, relative_url)

        price_text = price_element.get_text(strip=True)
        price_minor = parse_price_to_minor(price_text)

        if price_minor is None:
            logger.warning(
                "Skipping product card with unreadable price: %s",
                name,
            )
            continue

        # Assumption: the old price is marked with <del> or .old-price.
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

        # This site sells in GBP; a rupee sign or "Rs" means INR.
        currency = "INR" if ("₹" in price_text or "Rs" in price_text) else "GBP"

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


def _robots_allows(url: str, headers: dict[str, str]) -> bool:
    """Check robots.txt before fetching a page.

    HTTP 404 means robots.txt is absent and follows the project's
    existing policy of allowing the page fetch.

    Network failures, other HTTP errors, and redirects stop scraping.
    """
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
        raise RuntimeError(
            f"Unexpected redirect while fetching robots.txt: HTTP {response.status_code}"
        )

    if response.status_code == 404:
        logger.warning("robots.txt returned 404; allowing fetch of %s", url)
        return True

    if response.status_code >= 400:
        raise RuntimeError(f"robots.txt returned HTTP {response.status_code} for {url}")

    parser = RobotFileParser()
    parser.parse(response.text.splitlines())

    allowed = parser.can_fetch(settings.scrape_user_agent, url)

    if not allowed:
        logger.warning("robots.txt disallows fetching %s", url)

    return allowed


def fetch_html(url: str) -> str:
    """Fetch an HTML page while respecting robots.txt and request politeness.

    Failure handling:
    - Timeouts and connection errors are retried up to MAX_RETRIES times.
      The original network exception is raised if retries are exhausted.
    - HTTP 500, 502, 503, and 504 are retried up to MAX_RETRIES times.
      A RuntimeError is raised if retries are exhausted.
    - Other HTTP errors, including HTTP 404, fail immediately.
    - Robots.txt network failures, redirects, and HTTP errors other than
      404 stop scraping. A robots.txt 404 follows the existing policy of
      allowing the page fetch.
    - Page redirects, including external redirects, are rejected.
    - Non-HTML responses are rejected.
    - The configured User-Agent, timeout, request delay, and exponential
      retry backoff are preserved.

    Returns:
        The fetched HTML as a string.

    Raises:
        RuntimeError: If robots.txt disallows fetching, an HTTP error
            occurs, a redirect is rejected, or the response is not HTML.
        requests.Timeout: If timeout retries are exhausted.
        requests.ConnectionError: If connection retries are exhausted.
    """
    headers = {"User-Agent": settings.scrape_user_agent}
    logger.info("Using User-Agent: %s", headers["User-Agent"])

    if not _robots_allows(url, headers):
        logger.warning("robots.txt disallows fetching %s", url)
        raise RuntimeError(f"robots.txt disallows fetching {url}")

    # Wait before requesting the page after checking robots.txt.
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

        # Reject redirects rather than following them automatically.
        if 300 <= response.status_code < 400:
            location = response.headers.get("Location", "")

            if location:
                redirect_url = urljoin(url, location)

                original = urlsplit(url)
                redirected = urlsplit(redirect_url)

                original_origin = (
                    original.scheme.lower(),
                    (original.hostname or "").lower(),
                    original.port or (443 if original.scheme.lower() == "https" else 80),
                )

                redirected_origin = (
                    redirected.scheme.lower(),
                    (redirected.hostname or "").lower(),
                    redirected.port or (443 if redirected.scheme.lower() == "https" else 80),
                )

                if original_origin != redirected_origin:
                    raise RuntimeError(f"External redirect rejected: {url} -> {redirect_url}")

            raise RuntimeError(f"Unexpected redirect from {url}: HTTP {response.status_code}")

        # Retry only configured transient HTTP errors.
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

        # Reject responses that are not HTML.
        content_type = response.headers.get("Content-Type", "")
        media_type = content_type.split(";", maxsplit=1)[0].strip().lower()

        if media_type not in {"text/html", "application/xhtml+xml"}:
            raise RuntimeError(
                f"Expected HTML from {url}, received {content_type or 'unknown Content-Type'}"
            )

        logger.info("Fetched %s: HTTP %s", url, response.status_code)

        # Without an explicit charset, use requests' detected encoding.
        if "charset" not in content_type.lower():
            response.encoding = response.apparent_encoding

        return response.text

    raise RuntimeError(f"Failed to fetch {url} after {MAX_RETRIES + 1} attempts")


def scrape(url: str) -> list[ScrapedProduct]:
    """Fetch, save, parse, and return products.

    Fetch failures propagate to the caller. No raw HTML snapshot is saved
    when fetching fails.

    After a successful fetch, the raw HTML is saved before parsing so it
    remains available if parsing fails.

    Snapshot-saving OSError exceptions are logged but do not prevent
    parsing. Parsing exceptions propagate to the caller.

    Returns:
        A list of parsed ScrapedProduct objects.

    Raises:
        RuntimeError: If fetching fails due to robots.txt restrictions,
            an HTTP error, a rejected redirect, or a non-HTML response.
        requests.Timeout: If fetch timeout retries are exhausted.
        requests.ConnectionError: If connection retries are exhausted.
    """
    html = fetch_html(url)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    snapshot_path = SNAPSHOT_DIR / f"{timestamp}.html"

    # Save raw HTML before parsing for debugging and reprocessing.
    try:
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(html, encoding="utf-8")
    except OSError:
        logger.exception(
            "Could not save raw HTML snapshot to %s",
            snapshot_path,
        )

    return parse_listing(html, url)
