"""Scraper. Owners: Scraper track (2 people: parsing + robustness).

Contract: `scrape(url)` returns a list of ScrapedProduct and NEVER touches the database.
Keeping the scraper pure (HTML in, dataclasses out) means it can be unit-tested
against saved HTML files with zero network calls.
"""

import re

from dataclasses import dataclass
from datetime import datetime


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
    """'Rs. 1,299.50' / '₹1,299' / '1299' -> 129950 / 129900 / 129900. None if unparseable."""
    if not isinstance(text, str):
        return None
    value = text.strip()
    if not value:
        return None
    value = re.sub(r"^(?:Rs\.?|₹|£)\s*", "", value, flags=re.IGNORECASE)
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


def fetch_html(url: str) -> str:
    """GET with our User-Agent, a timeout, 2 retries with backoff, and respect for
    robots.txt. Raise a clear exception on 4xx/5xx."""
    raise NotImplementedError


def scrape(url: str) -> list[ScrapedProduct]:
    """fetch_html + save raw HTML to data/snapshots/ + parse_listing."""
    raise NotImplementedError
