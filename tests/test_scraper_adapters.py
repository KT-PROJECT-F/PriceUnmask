from backend.scraper.adapters.books_to_scrape import BooksToScrapeAdapter
from backend.scraper.adapters.legacy import LegacyScraperAdapter
from backend.scraper.registry import get_adapter


def test_books_adapter_accepts_books_url():
    adapter = BooksToScrapeAdapter()

    assert adapter.can_handle("https://books.toscrape.com/")


def test_books_adapter_rejects_other_url():
    adapter = BooksToScrapeAdapter()

    assert not adapter.can_handle("https://www.croma.com/")


def test_registry_selects_books_adapter():
    adapter = get_adapter("https://books.toscrape.com/")

    assert isinstance(adapter, BooksToScrapeAdapter)


def test_registry_preserves_legacy_fallback():
    adapter = get_adapter("https://www.croma.com/example/p/123")

    assert isinstance(adapter, LegacyScraperAdapter)
