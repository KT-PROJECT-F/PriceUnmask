from datetime import UTC
from pathlib import Path

import pytest

from backend.scraper.product_scraper import (
    parse_listing,
    parse_price_to_minor,
)


def test_parse_listing_sample_page():
    html = Path("data/snapshots/sample_books_page1.html").read_text(encoding="utf-8")
    products = parse_listing(html, "https://books.toscrape.com/")

    assert len(products) == 20

    first = products[0]

    assert first.external_id == "a-light-in-the-attic"
    assert first.name == "A Light in the Attic"
    assert first.url == (
        "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
    )

    assert first.current_price_minor == 5177
    assert first.in_stock is True
    assert first.currency == "GBP"
    assert first.original_price_minor is None
    assert first.scraped_at.tzinfo is UTC


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("£51.77", 5177),
        ("£52", 5200),
        ("£51.7", 5170),
        ("₹1,299.50", 129950),
        ("₹1,409", 140900),
        ("Rs. 999.99", 99999),
        ("Rs 999.99", 99999),
        ("1,299.50", 129950),
        ("  £22.30  ", 2230),
        ("₹ 700", 70000),
        ("", None),
        ("   ", None),
        ("£", None),
        ("Free", None),
        ("hello", None),
    ],
)
def test_parse_price_to_minor(text, expected):
    assert parse_price_to_minor(text) == expected
