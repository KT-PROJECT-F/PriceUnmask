from unittest.mock import patch

from backend.scraper.product_scraper import fetch_html


def test_fetch_html_success():
    fake_response = type(
        "FakeResponse",
        (),
        {
            "status_code": 200,
            "text": "<html><body>Test Product</body></html>",
        },
    )()

    with patch(
        "backend.scraper.product_scraper.requests.get",
        return_value=fake_response,
    ) as mock_get:
        html = fetch_html("https://example.com")

    assert html == "<html><body>Test Product</body></html>"
    mock_get.assert_called_once()


def test_fetch_html_uses_user_agent_and_timeout():
    fake_response = type(
        "FakeResponse",
        (),
        {
            "status_code": 200,
            "text": "<html>OK</html>",
        },
    )()

    with patch(
        "backend.scraper.product_scraper.requests.get",
        return_value=fake_response,
    ) as mock_get:
        fetch_html("https://example.com")

    mock_get.assert_called_once_with(
        "https://example.com",
        headers={"User-Agent": "PriceUnmaskBot/0.1 (learning project; contact: you@example.com)"},
        timeout=10,
    )


def test_fetch_html_raises_on_404():
    fake_response = type(
        "FakeResponse",
        (),
        {
            "status_code": 404,
            "text": "Not Found",
        },
    )()

    with patch(
        "backend.scraper.product_scraper.requests.get",
        return_value=fake_response,
    ):
        try:
            fetch_html("https://example.com/missing")
        except RuntimeError as exc:
            assert str(exc) == ("Failed to fetch https://example.com/missing: HTTP 404")
        else:
            raise AssertionError("Expected RuntimeError")


def test_fetch_html_raises_on_500():
    fake_response = type(
        "FakeResponse",
        (),
        {
            "status_code": 500,
            "text": "Server Error",
        },
    )()

    with patch(
        "backend.scraper.product_scraper.requests.get",
        return_value=fake_response,
    ):
        try:
            fetch_html("https://example.com/server-error")
        except RuntimeError as exc:
            assert str(exc) == ("Failed to fetch https://example.com/server-error: HTTP 500")
        else:
            raise AssertionError("Expected RuntimeError")
