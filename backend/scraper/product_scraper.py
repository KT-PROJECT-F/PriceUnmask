"""Scraper for product listing pages."""

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from backend.config import settings

FETCH_TIMEOUT_SECONDS = 10
MAX_RETRIES = 2
BACKOFF_SECONDS = 1

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
    """Convert a price string into minor currency units."""
    if not text or not text.strip():
        return None

    value = text.strip()

    currency_prefix = re.match(r"^(Rs\.?|₹|£)\s*", value, re.IGNORECASE)
    if currency_prefix:
        value = value[currency_prefix.end() :]

    value = value.replace(",", "")

    match = re.fullmatch(r"(\d+)(?:\.(\d{1,2}))?", value)
    if not match:
        return None

    whole = match.group(1)
    decimal = (match.group(2) or "").ljust(2, "0")

    return int(whole) * 100 + int(decimal)


def parse_listing(html: str, base_url: str) -> list[ScrapedProduct]:
    """Parse product cards from a listing page."""
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

        price_minor = parse_price_to_minor(price_element.get_text(strip=True))

        if price_minor is None:
            logger.warning("Skipping product card with unreadable price: %s", name)
            continue

        url_path = url.rstrip("/").split("/")
        filename = url_path[-1]

        slug = url_path[-2] if filename == "index.html" and len(url_path) >= 2 else filename

        external_id = slug.rsplit("_", 1)[0]

        price_text = price_element.get_text(strip=True)

        if "₹" in price_text:
            currency = "INR"
        elif "£" in price_text:
            currency = "GBP"
        elif "Rs" in price_text:
            currency = "INR"
        else:
            currency = "GBP"

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


def fetch_html(url: str) -> str:
    """GET with our User-Agent, a timeout, 2 retries with backoff, and respect for
    robots.txt. Raise a clear exception on 4xx/5xx."""
    response = requests.get(
        url,
        headers={"User-Agent": settings.scrape_user_agent},
        timeout=FETCH_TIMEOUT_SECONDS,
    )

    if response.status_code >= 400:
        raise RuntimeError(f"Failed to fetch {url}: HTTP {response.status_code}")

    # No charset in the header: requests guesses ISO-8859-1 and "£" becomes "Â£".
    if "charset" not in response.headers.get("Content-Type", "").lower():
        response.encoding = response.apparent_encoding

    return response.text


def scrape(url: str) -> list[ScrapedProduct]:
    """fetch_html + save raw HTML to data/snapshots/ + parse_listing."""
    raise NotImplementedError
