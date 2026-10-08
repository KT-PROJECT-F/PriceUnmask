"""Scraper. Owners: Scraper track (2 people: parsing + robustness).

Contract: `scrape(url)` returns a list of ScrapedProduct and NEVER touches the database.

Keeping the scraper pure (HTML in, dataclasses out) means it can be unit-tested
against saved HTML files with zero network calls.
"""

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import sleep
from urllib.parse import urljoin
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
    external_id: str  # stable id on the site (SKU, product slug from the URL, etc.)
    name: str
    url: str
    current_price_minor: int  # Rs 1,299.50 -> 129950
    original_price_minor: int | None  # strikethrough price, None if not shown
    in_stock: bool | None
    currency: str
    scraped_at: datetime  # timezone-aware UTC


def parse_price_to_minor(text: str) -> int | None:
    """'Rs. 1,299.50' / '£1,299' / '₹1,299' / '1299' -> minor units."""
    if not isinstance(text, str):
        return None
    value = text.strip()
    if not value:
        return None
    value = re.sub(
        r"^(?:Rs\.?|[£₹])\s*",
        "",
        value,
        flags=re.IGNORECASE,
    )
    value = value.replace(",", "").strip()
    match = re.fullmatch(r"(\d+)(?:\.(\d{1,2}))?", value)
    if not match:
        return None
    whole = match.group(1)
    decimal = match.group(2) or ""

    decimal = decimal.ljust(2, "0")
    return int(whole) * 100 + int(decimal)


def parse_listing(html: str, base_url: str) -> list[ScrapedProduct]:
    """Parse one listing page. Skip (and log) cards with missing name or price;
    never crash the whole page because one card is weird.
    """
    soup = BeautifulSoup(html, "html.parser")
    products: list[ScrapedProduct] = []
    scraped_at = datetime.now(UTC)
    cards = soup.select("article.product_pod")
    for card in cards:
        link = card.select_one("h3 a")
        price_element = card.select_one(".price_color")
        availability_element = card.select_one(".availability")
        if not link:
            logger.warning("Skipping product card with no product link")
            continue
        if not price_element:
            logger.warning("Skipping product card with no price")
            continue
        name = link.get("title") or link.get_text(strip=True)
        relative_url = link.get("href")
        if not relative_url:
            logger.warning("Skipping product card with no URL: %s", name)
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
                original_price_minor=None,
                in_stock=in_stock,
                currency=currency,
                scraped_at=scraped_at,
            )
        )
    return products


def _robots_allows(url: str, headers: dict[str, str]) -> bool:
    """Return whether robots.txt allows fetching the requested URL."""
    robots_url = urljoin(url, "/robots.txt")
    try:
        response = requests.get(
            robots_url,
            headers=headers,
            timeout=FETCH_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not fetch robots.txt for {url}: {exc}") from exc
    if response.status_code == 404:
        return True
    if response.status_code >= 400:
        raise RuntimeError(f"robots.txt returned HTTP {response.status_code} for {url}")
    parser = RobotFileParser()
    parser.parse(response.text.splitlines())
    return parser.can_fetch(settings.scrape_user_agent, url)


def fetch_html(url: str) -> str:
    """GET with our User-Agent, a timeout, 2 retries with backoff, and respect
    for robots.txt. Raise a clear exception on 4xx/5xx.
    """
    headers = {"User-Agent": settings.scrape_user_agent}
    if not _robots_allows(url, headers):
        raise RuntimeError(f"robots.txt disallows fetching {url}")
    # robots.txt and the page are two requests to the same site.
    # Wait politely before requesting the page.
    if settings.scrape_delay_seconds > 0:
        sleep(settings.scrape_delay_seconds)
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=FETCH_TIMEOUT_SECONDS,
            )
        except (requests.Timeout, requests.ConnectionError):
            if attempt == MAX_RETRIES:
                raise
            sleep(BACKOFF_SECONDS * (2**attempt))
            continue
        if response.status_code >= 400:
            if response.status_code not in RETRY_STATUSES:
                raise RuntimeError(f"Failed to fetch {url}: HTTP {response.status_code}")
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"Failed to fetch {url}: HTTP {response.status_code}")
            sleep(BACKOFF_SECONDS * (2**attempt))
            continue
        # No charset in the header: requests guesses ISO-8859-1.
        if "charset" not in response.headers.get("Content-Type", "").lower():
            response.encoding = response.apparent_encoding
        return response.text
    raise RuntimeError(f"Failed to fetch {url} after {MAX_RETRIES + 1} attempts")


def scrape(url: str) -> list[ScrapedProduct]:
    """Fetch, save raw HTML, parse, and return products."""
    html = fetch_html(url)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    snapshot_path = SNAPSHOT_DIR / f"{timestamp}.html"

    # Keep the raw page first: if the parser has a bug, we can re-parse it later.
    # A failed backup must not cost us the prices, so we only log it.
    try:
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(html, encoding="utf-8")
    except OSError:
        logger.exception("Could not save raw HTML snapshot to %s", snapshot_path)

    return parse_listing(html, url)
