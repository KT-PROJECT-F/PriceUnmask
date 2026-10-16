import logging
from datetime import UTC
from html import escape
from pathlib import Path

import pytest

from backend.scraper.product_scraper import (
    parse_listing,
    parse_next_page_url,
    parse_price_to_minor,
)

SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "data" / "snapshots"

FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "snapshots" / "sample_books_page1.html"
)
BROKEN_FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "snapshots" / "sample_books_broken.html"
)
CATEGORY_FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "snapshots" / "sample_books_category.html"
)


BASE_URL = "https://books.toscrape.com/"
CATEGORY_BASE_URL = "https://books.toscrape.com/catalogue/category/books/travel_2/index.html"


def parse_fixture(fixture_path: Path, base_url: str) -> list:
    html = fixture_path.read_text(encoding="utf-8")
    return parse_listing(html, base_url)


def test_parse_listing_sample_page():
    html = FIXTURE_PATH.read_text(encoding="utf-8")

    products = parse_listing(
        html,
        "https://books.toscrape.com/",
    )

    assert len(products) == 20
    assert len({product.external_id for product in products}) == 20

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


def test_parse_listing_sample_page_has_unique_ids_and_int_prices():
    html = FIXTURE_PATH.read_text(encoding="utf-8")

    products = parse_listing(html, "https://books.toscrape.com/")

    assert len({p.external_id for p in products}) == 20
    assert all(isinstance(p.current_price_minor, int) for p in products)
    assert all(p.url.startswith("https://books.toscrape.com/") for p in products)


def test_parse_listing_skips_card_without_href():
    html = """
    <article class="product_pod">
        <h3><a title="Book One">Book One</a></h3>
        <p class="price_color">£10.00</p>
    </article>
    """

    assert parse_listing(html, "https://books.toscrape.com/") == []


def test_parse_listing_skips_card_without_link():
    html = """
    <article class="product_pod">
        <h3></h3>
        <p class="price_color">£10.00</p>
    </article>
    """

    assert parse_listing(html, "https://books.toscrape.com/") == []


def test_parse_listing_missing_availability_gives_unknown_stock():
    html = """
    <article class="product_pod">
        <h3><a href="book_1/index.html" title="Book One">Book One</a></h3>
        <p class="price_color">£10.00</p>
    </article>
    """

    products = parse_listing(html, "https://books.toscrape.com/")

    assert len(products) == 1
    assert products[0].in_stock is None


def test_parse_price_to_minor_non_string_returns_none():
    assert parse_price_to_minor(None) is None
    assert parse_price_to_minor(5) is None


def test_parse_listing_skips_card_without_price():
    html = """
    <article class="product_pod">
        <h3>
            <a href="book_1/index.html" title="Book One">
                Book One
            </a>
        </h3>
        <div class="availability">
            In stock
        </div>
    </article>
    """

    products = parse_listing(
        html,
        "https://books.toscrape.com/",
    )

    assert products == []


def test_parse_listing_skips_unreadable_price():
    html = """
    <article class="product_pod">
        <h3>
            <a href="book_1/index.html" title="Book One">
                Book One
            </a>
        </h3>
        <p class="price_color">Not available</p>
        <div class="availability">
            In stock
        </div>
    </article>
    """

    products = parse_listing(
        html,
        "https://books.toscrape.com/",
    )

    assert products == []


def test_parse_listing_out_of_stock_book():
    html = """
    <article class="product_pod">
        <h3>
            <a href="book_1/index.html" title="Book One">
                Book One
            </a>
        </h3>
        <p class="price_color">£20.00</p>
        <div class="availability">
            Out of stock
        </div>
    </article>
    """

    products = parse_listing(
        html,
        "https://books.toscrape.com/",
    )

    assert len(products) == 1
    assert products[0].in_stock is False


def test_parse_listing_empty_html():
    products = parse_listing(
        "",
        "https://books.toscrape.com/",
    )

    assert products == []


def test_parse_listing_rupee_currency():
    html = """
    <article class="product_pod">
        <h3>
            <a href="book_1/index.html" title="Book One">
                Book One
            </a>
        </h3>
        <p class="price_color">₹1,299</p>
        <div class="availability">
            In stock
        </div>
    </article>
    """

    products = parse_listing(
        html,
        "https://example.com/",
    )

    assert len(products) == 1
    assert products[0].current_price_minor == 129900
    assert products[0].currency == "INR"


def test_parse_listing_same_timestamp_for_page():
    html = """
    <article class="product_pod">
        <h3>
            <a href="book_1/index.html" title="Book One">
                Book One
            </a>
        </h3>
        <p class="price_color">£10.00</p>
        <div class="availability">
            In stock
        </div>
    </article>

    <article class="product_pod">
        <h3>
            <a href="book_2/index.html" title="Book Two">
                Book Two
            </a>
        </h3>
        <p class="price_color">£20.00</p>
        <div class="availability">
            In stock
        </div>
    </article>
    """

    products = parse_listing(
        html,
        "https://books.toscrape.com/",
    )

    assert len(products) == 2
    assert products[0].scraped_at == products[1].scraped_at


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
        ("N/A", None),
        ("Call for price", None),
    ],
)
def test_parse_price_to_minor(text, expected):
    assert parse_price_to_minor(text) == expected


def parse_broken_fixture():
    html = BROKEN_FIXTURE_PATH.read_text(encoding="utf-8")
    return parse_listing(html, "https://books.toscrape.com/")


def test_parse_listing_broken_fixture_skips_damaged_cards():
    products = parse_broken_fixture()

    # 22 cards in the file; 4 are damaged:
    # no price, unreadable price, no product link, and no name.
    assert len(products) == 18

    names = {product.name for product in products}

    assert "A Light in the Attic" not in names
    assert "Tipping the Velvet" not in names
    assert "Broken Product" not in names


def test_parse_listing_broken_fixture_logs_each_skipped_card(caplog):
    with caplog.at_level("WARNING"):
        parse_broken_fixture()

    assert "no price: A Light in the Attic" in caplog.text
    assert "unreadable price: Tipping the Velvet" in caplog.text
    assert "no product link" in caplog.text
    assert "no name" in caplog.text
    assert len(caplog.records) == 4


def test_parse_listing_broken_fixture_out_of_stock():
    products = parse_broken_fixture()

    book = next(product for product in products if product.name == "The Black Maria")

    assert book.in_stock is False


def test_parse_listing_broken_fixture_reads_original_price():
    products = parse_broken_fixture()

    product = next(
        product for product in products if product.name.startswith("The Boys in the Boat")
    )

    assert product.current_price_minor == 2260
    assert product.original_price_minor == 5000


def test_parse_listing_broken_fixture_continues_after_bad_cards():
    products = parse_broken_fixture()

    assert len(products) == 18
    assert all(product.name for product in products)
    assert all(product.current_price_minor > 0 for product in products)

    names = {product.name for product in products}

    assert "A Light in the Attic" not in names
    assert "Tipping the Velvet" not in names
    assert "Broken Product" not in names


def test_parse_listing_ignores_old_price_not_above_price():
    html = """
    <article class="product_pod">
        <h3>
            <a href="a_1/index.html" title="A">A</a>
        </h3>
        <p class="price_color">£10.00</p>
        <del>£5.00</del>
    </article>
    """

    [product] = parse_listing(
        html,
        "https://books.toscrape.com/",
    )

    assert product.current_price_minor == 1000
    assert product.original_price_minor is None


def test_parse_listing_logs_error_when_every_card_is_skipped(caplog):
    html = """
    <article class="product_pod">
        <h3>
            <a href="a_1/index.html" title="A">A</a>
        </h3>
    </article>
    """

    with caplog.at_level("ERROR"):
        products = parse_listing(
            html,
            "https://books.toscrape.com/",
        )

    assert products == []
    assert "Skipped all 1 product cards" in caplog.text


def test_parse_category_page_returns_books():
    products = parse_fixture(CATEGORY_FIXTURE_PATH, CATEGORY_BASE_URL)

    assert len(products) == 11


def test_parse_category_page_returns_exact_urls():
    products = parse_fixture(CATEGORY_FIXTURE_PATH, CATEGORY_BASE_URL)

    assert len(products) == 11

    assert products[0].url == (
        "https://books.toscrape.com/catalogue/its-only-the-himalayas_981/index.html"
    )

    assert all(
        product.url.startswith("https://books.toscrape.com/catalogue/") for product in products
    )


def test_parse_category_page_reads_product_fields():
    products = parse_fixture(CATEGORY_FIXTURE_PATH, CATEGORY_BASE_URL)

    assert len(products) == 11

    product = products[0]

    assert product.name == "It's Only the Himalayas"
    assert product.current_price_minor == 4517
    assert product.in_stock is True
    assert product.currency == "GBP"
    assert product.scraped_at.tzinfo is UTC


def make_book_card(
    title: str = "Example Book",
    href: str = "catalogue/example-book_1000/index.html",
    price: str | None = "£10.00",
    rating: bool = True,
) -> str:
    """Create a small HTML book card for parser tests."""
    price_html = f'<p class="price_color">{price}</p>' if price is not None else ""

    rating_html = '<p class="star-rating Three"></p>' if rating else ""

    return f"""
    <article class="product_pod">
        <h3>
          <a href="{escape(href, quote=True)}" title="{escape(title, quote=True)}">
            {escape(title[:20])}...
          </a>
        </h3>
       {rating_html}
       <div class="product_price">
        {price_html}
        <p class="availability">In stock</p>
       </div>
</article>
"""


def make_listing(*cards: str) -> str:
    """Combine book cards into one listing page."""
    return "<html><body>" + "".join(cards) + "</body></html>"


def test_long_title_uses_full_title_attribute():
    full_title = "The Complete Guide to Python Programming for Beginners"
    html = make_listing(make_book_card(title=full_title))

    products = parse_listing(html, BASE_URL)

    assert len(products) == 1
    assert products[0].name == full_title


def test_non_ascii_title_is_preserved():
    title = "Café München — 日本語"
    html = make_listing(make_book_card(title=title))

    products = parse_listing(html, BASE_URL)

    assert len(products) == 1
    assert products[0].name == title


def test_missing_price_skips_card_and_logs_warning(caplog):
    broken_card = make_book_card(
        title="Book Without Price",
        href="catalogue/no-price_1001/index.html",
        price=None,
    )
    valid_card = make_book_card(
        title="Valid Book",
        href="catalogue/valid-book_1002/index.html",
    )
    html = make_listing(broken_card, valid_card)

    with caplog.at_level(logging.WARNING):
        products = parse_listing(html, BASE_URL)

    assert len(products) == 1
    assert products[0].name == "Valid Book"
    assert "no price: Book Without Price" in caplog.text
    assert len(caplog.records) == 1


def test_missing_rating_does_not_skip_book():
    # ScrapedProduct has no rating field. This guards against a future
    # change that makes the parser require a rating and drop the card.
    html = make_listing(
        make_book_card(
            title="Book Without Rating",
            href="catalogue/no-rating_1003/index.html",
            rating=False,
        )
    )

    products = parse_listing(html, BASE_URL)

    assert len(products) == 1
    assert products[0].name == "Book Without Rating"
    assert products[0].current_price_minor == 1000
    assert products[0].in_stock is True


def test_title_with_quotes_is_preserved():
    title = 'The "Real" Story'
    html = make_listing(make_book_card(title=title))

    products = parse_listing(html, BASE_URL)

    assert len(products) == 1
    assert products[0].name == title


def read_html(filename: str) -> str:
    return (SNAPSHOT_DIR / filename).read_text(encoding="utf-8")


def test_page1_next_url():
    html = read_html("sample_books_page1.html")

    assert (
        parse_next_page_url(
            html,
            "https://books.toscrape.com/",
        )
        == "https://books.toscrape.com/catalogue/page-2.html"
    )


def test_page25_next_url():
    html = read_html("sample_books_page25.html")

    assert (
        parse_next_page_url(
            html,
            "https://books.toscrape.com/catalogue/page-25.html",
        )
        == "https://books.toscrape.com/catalogue/page-26.html"
    )


def test_page50_has_no_next_url():
    html = read_html("sample_books_page50.html")

    assert (
        parse_next_page_url(
            html,
            "https://books.toscrape.com/catalogue/page-50.html",
        )
        is None
    )
