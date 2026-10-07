"""Scraper. Owners: Scraper track (2 people: parsing + robustness).

Contract: scrape(url) returns a list of ScrapedProduct and NEVER touches
the database. Keeping the scraper pure (HTML in, dataclasses out) means
it can be unit-tested against saved HTML files with zero network calls.
"""

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from time import sleep
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import requests

from backend.config import settings

FETCH_TIMEOUT_SECONDS = 10
MAX_RETRIES = 2
BACKOFF_SECONDS = 1


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
    """Convert a price string into minor currency units."""
    if not text or not text.strip():
        return None

    # Remove common currency prefixes, including Rs. and Rs.
    cleaned_text = re.sub(r"(?i)^\s*Rs\.?\s*", "", text.strip())

    # Remove thousands separators and currency symbols.
    cleaned_text = cleaned_text.replace(",", "")
    cleaned_text = re.sub(r"[^\d.]", "", cleaned_text)

    # Reject empty or malformed numeric values.
    if not cleaned_text or cleaned_text.count(".") > 1:
        return None

    try:
        price = Decimal(cleaned_text)
    except InvalidOperation:
        return None

    if not price.is_finite() or price < 0:
        return None

    return int(price * 100)


def parse_listing(html: str, base_url: str) -> list[ScrapedProduct]:
    """Parse a listing page into ScrapedProduct objects.

    HTML-specific parsing is not implemented in this version.
    """
    raise NotImplementedError("Listing HTML parsing has not been implemented yet.")


def fetch_html(url: str) -> str:
    """Fetch a page with a User-Agent, timeout, retries, and robots.txt."""
    robots_url = urljoin(url, "/robots.txt")
    headers = {"User-Agent": settings.scrape_user_agent}

    robots_response = requests.get(
        robots_url,
        headers=headers,
        timeout=FETCH_TIMEOUT_SECONDS,
    )

    if robots_response.status_code == 404:
        robots_allowed = True
    elif robots_response.status_code >= 400:
        raise RuntimeError(
            f"Failed to fetch robots.txt for {url}: HTTP {robots_response.status_code}"
        )
    else:
        parser = RobotFileParser()
        parser.parse(robots_response.text.splitlines())
        robots_allowed = parser.can_fetch(settings.scrape_user_agent, url)

    if not robots_allowed:
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
            if response.status_code not in (500, 503):
                raise RuntimeError(f"Failed to fetch {url}: HTTP {response.status_code}")

            if attempt == MAX_RETRIES:
                raise RuntimeError(f"Failed to fetch {url}: HTTP {response.status_code}")

            sleep(BACKOFF_SECONDS * (2**attempt))
            continue

        if "charset" not in response.headers.get("Content-Type", "").lower():
            response.encoding = response.apparent_encoding

        return response.text

    raise RuntimeError(f"Failed to fetch {url} after {MAX_RETRIES + 1} attempts")


def scrape(url: str) -> list[ScrapedProduct]:
    """Fetch HTML and parse the listing."""
    html = fetch_html(url)
    return parse_listing(html, url)
