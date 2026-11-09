from typing import Protocol

from backend.scraper.product_scraper import ScrapedProduct


class SourceAdapter(Protocol):
    """Contract that every product-source adapter must implement."""

    source_name: str

    def can_handle(self, url: str) -> bool:
        """Return True when this adapter supports the URL."""
        ...

    def scrape(self, url: str) -> list[ScrapedProduct]:
        """Fetch and parse products without accessing the database."""
        ...
