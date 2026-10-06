import pytest

from backend.config import settings
from backend.scraper.product_scraper import fetch_html


class FakeResponse:
    def __init__(
        self,
        status_code=200,
        text="",
        content=b"",
        encoding=None,
        apparent_encoding="utf-8",
        headers=None,
    ):
        self.status_code = status_code
        self.text = text
        self.content = content
        self.encoding = encoding
        self.apparent_encoding = apparent_encoding
        self.headers = headers or {}


def test_fetch_html_success(monkeypatch):
    fake_response = FakeResponse(
        text="<html><body>Test Product</body></html>"
    )

    monkeypatch.setattr(
        "backend.scraper.product_scraper.requests.get",
        lambda *args, **kwargs: fake_response,
    )

    html = fetch_html("https://example.com")

    assert html == "<html><body>Test Product</body></html>"


def test_fetch_html_uses_user_agent_and_timeout(monkeypatch):
    fake_response = FakeResponse(text="<html>OK</html>")
    captured = {}

    def fake_get(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return fake_response

    monkeypatch.setattr(
        "backend.scraper.product_scraper.requests.get",
        fake_get,
    )

    fetch_html("https://example.com")

    assert captured["args"] == ("https://example.com",)
    assert captured["kwargs"] == {
        "headers": {"User-Agent": settings.scrape_user_agent},
        "timeout": 10,
    }


def test_fetch_html_raises_on_404(monkeypatch):
    monkeypatch.setattr(
        "backend.scraper.product_scraper.requests.get",
        lambda *args, **kwargs: FakeResponse(status_code=404),
    )

    with pytest.raises(RuntimeError, match="HTTP 404"):
        fetch_html("https://example.com/missing")


def test_fetch_html_raises_on_500(monkeypatch):
    monkeypatch.setattr(
        "backend.scraper.product_scraper.requests.get",
        lambda *args, **kwargs: FakeResponse(status_code=500),
    )

    with pytest.raises(RuntimeError, match="HTTP 500"):
        fetch_html("https://example.com/server-error")


def test_fetch_html_handles_missing_charset(monkeypatch):
    fake_response = FakeResponse(
        content="£51.77".encode(),
        encoding=None,
        apparent_encoding="utf-8",
        headers={"Content-Type": "text/html"},
    )

    @property
    def text(self):
        return self.content.decode(self.encoding or "utf-8")

    FakeResponse.text = text

    monkeypatch.setattr(
        "backend.scraper.product_scraper.requests.get",
        lambda *args, **kwargs: fake_response,
    )

    html = fetch_html("https://example.com")

    assert "£51.77" in html
    assert "Â£" not in html