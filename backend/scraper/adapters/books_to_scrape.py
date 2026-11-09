from dataclasses import replace
from urllib.parse import urlsplit

from backend.scraper.product_scraper import (
    ScrapedProduct,
)
from backend.scraper.product_scraper import (
    scrape as scrape_books,
)


class BooksToScrapeAdapter:
    source_name = "books-toscrape"

    def can_handle(self, url: str) -> bool:
        return urlsplit(url).hostname in {
            "books.toscrape.com",
            "www.books.toscrape.com",
        }

    def scrape(self, url: str) -> list[ScrapedProduct]:
        products = scrape_books(url)

        # Preserve the existing parser output and add a stable source key.
        return [replace(product, source=self.source_name) for product in products]
