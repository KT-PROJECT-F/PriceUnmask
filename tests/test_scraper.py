import pytest

from backend.scraper.product_scraper import parse_price_to_minor


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
