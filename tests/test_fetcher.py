import pytest

from backend.config import settings
from backend.scraper.product_scraper import FETCH_TIMEOUT_SECONDS, fetch_html


class FakeResponse:
    """Behaves like requests: no charset in Content-Type -> encoding ISO-8859-1."""

    def __init__(
        self,
        status_code: int = 200,
        body: str = "",
        content_type: str = "text/html; charset=utf-8",
    ) -> None:
        self.status_code = status_code
        self.content = body.encode("utf-8")
        self.headers = {"Content-Type": content_type}
        self.encoding = "utf-8" if "charset=utf-8" in content_type else "ISO-8859-1"
        self.apparent_encoding = "utf-8"

    @property
    def text(self) -> str:
        return self.content.decode(self.encoding)


def use_fake(monkeypatch, response: FakeResponse, calls: list | None = None) -> None:
    def fake_get(url, **kwargs):
        if calls is not None:
            calls.append((url, kwargs))
        return response

    monkeypatch.setattr(
        "backend.scraper.product_scraper.requests.get",
        fake_get,
    )


def test_success(monkeypatch) -> None:
    use_fake(monkeypatch, FakeResponse(body="<html>OK</html>"))
    assert fetch_html("https://example.com") == "<html>OK</html>"


def test_user_agent_and_timeout(monkeypatch) -> None:
    calls: list = []
    use_fake(monkeypatch, FakeResponse(body="ok"), calls)
    fetch_html("https://example.com")

    _, kwargs = calls[0]

    assert kwargs["headers"]["User-Agent"] == settings.scrape_user_agent
    assert kwargs["timeout"] == FETCH_TIMEOUT_SECONDS


@pytest.mark.parametrize("status", [404, 500])
def test_error_status_raises(monkeypatch, status: int) -> None:
    use_fake(monkeypatch, FakeResponse(status_code=status))

    with pytest.raises(RuntimeError, match=f"HTTP {status}"):
        fetch_html("https://example.com/x")


def test_pound_sign_survives_without_charset(monkeypatch) -> None:
    use_fake(
        monkeypatch,
        FakeResponse(
            body="<p>£51.77</p>",
            content_type="text/html",
        ),
    )

    html = fetch_html("https://books.toscrape.com")

    assert "£51.77" in html
    assert "Â£" not in html


def test_fake_garbles_like_requests_without_fix() -> None:
    assert (
        "Â£"
        in FakeResponse(
            body="£",
            content_type="text/html",
        ).text
    )
