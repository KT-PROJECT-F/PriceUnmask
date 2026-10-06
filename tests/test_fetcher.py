import pytest
import requests

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


def use_fake(monkeypatch, responses, calls: list | None = None) -> None:
    response_list = list(responses)

    def fake_get(url, **kwargs):
        if calls is not None:
            calls.append((url, kwargs))

        response = response_list.pop(0)

        if isinstance(response, Exception):
            raise response

        return response

    monkeypatch.setattr(
        "backend.scraper.product_scraper.requests.get",
        fake_get,
    )


def test_success(monkeypatch) -> None:
    use_fake(
        monkeypatch,
        [
            FakeResponse(body="User-agent: *\nAllow: /"),
            FakeResponse(body="<html>OK</html>"),
        ],
    )

    assert fetch_html("https://example.com") == "<html>OK</html>"


def test_user_agent_and_timeout(monkeypatch) -> None:
    calls: list = []

    use_fake(
        monkeypatch,
        [
            FakeResponse(body="User-agent: *\nAllow: /"),
            FakeResponse(body="ok"),
        ],
        calls,
    )

    fetch_html("https://example.com")

    _, kwargs = calls[1]

    assert kwargs["headers"]["User-Agent"] == settings.scrape_user_agent
    assert kwargs["timeout"] == FETCH_TIMEOUT_SECONDS


def test_pound_sign_survives_without_charset(monkeypatch) -> None:
    use_fake(
        monkeypatch,
        [
            FakeResponse(body="User-agent: *\nAllow: /"),
            FakeResponse(
                body="<p>£51.77</p>",
                content_type="text/html",
            ),
        ],
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


def test_retries_twice_then_succeeds(monkeypatch) -> None:
    calls: list = []
    sleeps: list = []

    use_fake(
        monkeypatch,
        [
            FakeResponse(body="User-agent: *\nAllow: /"),
            requests.ConnectionError("temporary failure"),
            requests.ConnectionError("temporary failure"),
            FakeResponse(body="<html>OK</html>"),
        ],
        calls,
    )

    monkeypatch.setattr(
        "backend.scraper.product_scraper.sleep",
        lambda seconds: sleeps.append(seconds),
    )

    assert fetch_html("https://example.com") == "<html>OK</html>"
    assert len(calls) == 4
    assert sleeps == [1, 2]


def test_retries_twice_then_raises(monkeypatch) -> None:
    calls: list = []
    sleeps: list = []

    use_fake(
        monkeypatch,
        [
            FakeResponse(body="User-agent: *\nAllow: /"),
            requests.Timeout("temporary failure"),
            requests.Timeout("temporary failure"),
            requests.Timeout("temporary failure"),
        ],
        calls,
    )

    monkeypatch.setattr(
        "backend.scraper.product_scraper.sleep",
        lambda seconds: sleeps.append(seconds),
    )

    with pytest.raises(requests.Timeout):
        fetch_html("https://example.com")

    assert len(calls) == 4
    assert sleeps == [1, 2]


def test_404_is_not_retried(monkeypatch) -> None:
    calls: list = []

    use_fake(
        monkeypatch,
        [
            FakeResponse(body="User-agent: *\nAllow: /"),
            FakeResponse(status_code=404),
        ],
        calls,
    )

    with pytest.raises(RuntimeError, match="HTTP 404"):
        fetch_html("https://example.com/missing")

    assert len(calls) == 2


def test_disallowed_url_raises_before_page_request(monkeypatch) -> None:
    calls: list = []

    use_fake(
        monkeypatch,
        [
            FakeResponse(body="User-agent: *\nDisallow: /private/"),
        ],
        calls,
    )

    with pytest.raises(RuntimeError, match="robots.txt disallows"):
        fetch_html("https://example.com/private/product")

    assert len(calls) == 1
    assert calls[0][0] == "https://example.com/robots.txt"


def test_503_retries_then_succeeds(monkeypatch) -> None:
    calls: list = []
    sleeps: list = []

    use_fake(
        monkeypatch,
        [
            FakeResponse(body="User-agent: *\nAllow: /"),
            FakeResponse(status_code=503),
            FakeResponse(status_code=503),
            FakeResponse(body="<html>OK</html>"),
        ],
        calls,
    )

    monkeypatch.setattr(
        "backend.scraper.product_scraper.sleep",
        lambda seconds: sleeps.append(seconds),
    )

    assert fetch_html("https://example.com") == "<html>OK</html>"
    assert len(calls) == 4
    assert sleeps == [1, 2]
