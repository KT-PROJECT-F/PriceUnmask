from backend.scraper.product_scraper import (
    ScrapedProduct,
)
from backend.scraper.product_scraper import (
    scrape as scrape_existing,
)


class LegacyScraperAdapter:
    """Temporary fallback preserving existing scraper behaviour."""

    source_name = "legacy"

    def can_handle(self, url: str) -> bool:
        return True

    def scrape(self, url: str) -> list[ScrapedProduct]:
        return scrape_existing(url)
