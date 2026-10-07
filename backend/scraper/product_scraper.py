"""Scraper. Owners: Scraper track (2 people: parsing + robustness).

Contract: `scrape(url)` returns a list of ScrapedProduct and NEVER touches the database.
Keeping the scraper pure (HTML in, dataclasses out) means it can be unit-tested
against saved HTML files with zero network calls.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from time import sleep
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import requests

from backend.config import settings

FETCH_TIMEOUT_SECONDS = 10
MAX_RETRIES = 2
BACKOFF_SECONDS = 1

RETRY_STATUSES = {500, 502, 503, 504}


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
    decimal = match.group(2) or ""

    decimal = decimal.ljust(2, "0")
    return int(whole) * 100 + int(decimal)


def parse_listing(html: str, base_url: str) -> list[ScrapedProduct]:
    """Parse one listing page. Skip (and log) cards with missing name or price;
    never crash the whole page because one card is weird."""
    raise NotImplementedError


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
    """GET with our User-Agent, a timeout, 2 retries with backoff, and respect for
    robots.txt. Raise a clear exception on 4xx/5xx."""
    headers = {"User-Agent": settings.scrape_user_agent}

    if not _robots_allows(url, headers):
        raise RuntimeError(f"robots.txt disallows fetching {url}")

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

        # No charset in the header: requests guesses ISO-8859-1 and
        # "┬ú" becomes "├é┬ú".
        if "charset" not in response.headers.get("Content-Type", "").lower():
            response.encoding = response.apparent_encoding

        return response.text

    raise RuntimeError(f"Failed to fetch {url} after {MAX_RETRIES + 1} attempts")


def scrape(url: str) -> list[ScrapedProduct]:
    """fetch_html + save raw HTML to data/snapshots/ + parse_listing."""
    raise NotImplementedError
