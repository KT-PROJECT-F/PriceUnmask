from backend.scraper.adapters.base import SourceAdapter
from backend.scraper.adapters.books_to_scrape import BooksToScrapeAdapter
from backend.scraper.adapters.legacy import LegacyScraperAdapter
from backend.scraper.product_scraper import ScrapedProduct

ADAPTERS: tuple[SourceAdapter, ...] = (
    BooksToScrapeAdapter(),
    LegacyScraperAdapter(),
)


def get_adapter(url: str) -> SourceAdapter:
    """Return the first adapter that supports the URL."""

    for adapter in ADAPTERS:
        if adapter.can_handle(url):
            return adapter

    raise ValueError(f"No scraper adapter found for URL: {url}")


def scrape(url: str) -> list[ScrapedProduct]:
    """Dispatch scraping to the appropriate adapter."""

    adapter = get_adapter(url)
    return adapter.scrape(url)
