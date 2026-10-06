"""Scraper. Owners: Scraper track (2 people: parsing + robustness).

Contract: `scrape(url)` returns a list of ScrapedProduct and NEVER touches the database.
Keeping the scraper pure (HTML in, dataclasses out) means it can be unit-tested
against saved HTML files with zero network calls.
"""

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from backend.config import settings

FETCH_TIMEOUT_SECONDS = 10


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
    # Convert the HTML string into a BeautifulSoup object
    soup = BeautifulSoup(html, "html.parser")

    # Store all scraped products
    products = []

    # Find every product card on the listing page
    for card in soup.select("article.product_pod"):
        # Find the product link/name
        link = card.select_one("h3 a")

        # Find the product price
        price_element = card.select_one(".price_color")

        # Find the availability information
        availability_element = card.select_one(".availability")

        # Skip this product if any required element is missing
        if not link or not price_element or not availability_element:
            continue

        # Get the product's relative URL from the HTML
        relative_url = link.get("href", "")

        # Convert the relative URL into a complete URL
        url = urljoin(base_url, relative_url)

        # Use the last part of the URL as the product ID
        external_id = url.rstrip("/").split("/")[-2].rsplit("_", 1)[0]

        # Get the product name from the title attribute or link text
        name = link.get("title") or link.get_text(strip=True)

        # Get the price as text
        price_text = price_element.get_text(strip=True)

        # Convert the price into minor currency units
        price_minor = parse_price_to_minor(price_text)

        # Get availability text and clean extra spaces
        availability = availability_element.get_text(" ", strip=True)

        # Check whether the product is currently in stock
        in_stock = "In stock" in availability

        # Create a ScrapedProduct object and add it to the list
        products.append(
            ScrapedProduct(
                external_id=external_id,
                name=name,
                url=url,
                current_price_minor=price_minor,
                original_price_minor=None,
                in_stock=in_stock,
                currency="GBP",
                scraped_at=datetime.now(UTC),
            )
        )

    # Return all products found on the page
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
