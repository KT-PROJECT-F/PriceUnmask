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
    calls: list = []
    use_fake(monkeypatch, FakeResponse(body="<html>OK</html>"), calls)

    assert fetch_html("https://example.com") == "<html>OK</html>"
    assert len(calls) == 2


def test_user_agent_and_timeout(monkeypatch) -> None:
    calls: list = []
    use_fake(monkeypatch, FakeResponse(body="ok"), calls)

    fetch_html("https://example.com")

    _, kwargs = calls[0]

    assert kwargs["headers"]["User-Agent"] == settings.scrape_user_agent
    assert kwargs["timeout"] == FETCH_TIMEOUT_SECONDS


@pytest.mark.parametrize("status", [404, 500])
def test_error_status_raises(monkeypatch, status: int) -> None:
    if status == 404:
        responses = [
            FakeResponse(body="User-agent: *\nAllow: /"),
            FakeResponse(status_code=404),
        ]
    else:
        responses = [
            FakeResponse(body="User-agent: *\nAllow: /"),
            FakeResponse(status_code=500),
            FakeResponse(status_code=500),
            FakeResponse(status_code=500),
        ]

    queue = list(responses)

    def fake_get(url, **kwargs):
        return queue.pop(0)

    monkeypatch.setattr(
        "backend.scraper.product_scraper.requests.get",
        fake_get,
    )

    with pytest.raises(RuntimeError, match=f"HTTP {status}"):
        fetch_html("https://example.com/x")


def test_pound_sign_survives_without_charset(monkeypatch) -> None:
    responses = [
        FakeResponse(body="User-agent: *\nAllow: /"),
        FakeResponse(
            body="<p>┬ú51.77</p>",
            content_type="text/html",
        ),
    ]

    queue = list(responses)

    def fake_get(url, **kwargs):
        return queue.pop(0)

    monkeypatch.setattr(
        "backend.scraper.product_scraper.requests.get",
        fake_get,
    )

    html = fetch_html("https://books.toscrape.com")

    assert "┬ú51.77" in html
    assert "├é┬ú" not in html


def test_fake_garbles_like_requests_without_fix() -> None:
    assert (
        "Â£"
        in FakeResponse(
            body="£",
            content_type="text/html",
        ).text
    )


@pytest.fixture
def sleeps(monkeypatch):
    waits: list[float] = []
    monkeypatch.setattr(
        "backend.scraper.product_scraper.sleep",
        waits.append,
    )
    return waits


def script(monkeypatch, *steps):
    """steps are FakeResponse objects or exceptions, returned/raised in order."""
    calls: list[str] = []
    queue = list(steps)

    def fake_get(url, **kwargs):
        calls.append(url)
        step = queue.pop(0)

        if isinstance(step, Exception):
            raise step

        return step

    monkeypatch.setattr(
        "backend.scraper.product_scraper.requests.get",
        fake_get,
    )

    return calls


ROBOTS_OK = FakeResponse(
    body="User-agent: *\nAllow: /",
)


def test_fails_twice_then_succeeds(monkeypatch, sleeps) -> None:
    calls = script(
        monkeypatch,
        ROBOTS_OK,
        FakeResponse(503),
        FakeResponse(503),
        FakeResponse(body="ok"),
    )

    assert fetch_html("https://example.com/p") == "ok"
    assert len(calls) == 4
    assert sleeps == [1, 2]


def test_fails_three_times_then_raises(monkeypatch, sleeps) -> None:
    script(
        monkeypatch,
        ROBOTS_OK,
        FakeResponse(503),
        FakeResponse(503),
        FakeResponse(503),
    )

    with pytest.raises(RuntimeError, match="HTTP 503"):
        fetch_html("https://example.com/p")

    assert sleeps == [1, 2]


def test_404_is_not_retried(monkeypatch, sleeps) -> None:
    calls = script(
        monkeypatch,
        ROBOTS_OK,
        FakeResponse(404),
    )

    with pytest.raises(RuntimeError, match="HTTP 404"):
        fetch_html("https://example.com/p")

    assert len(calls) == 2
    assert sleeps == []


def test_timeout_is_retried(monkeypatch, sleeps) -> None:
    script(
        monkeypatch,
        ROBOTS_OK,
        requests.Timeout(),
        FakeResponse(body="ok"),
    )

    assert fetch_html("https://example.com/p") == "ok"
    assert sleeps == [1]


def test_disallowed_url_never_requests_the_page(monkeypatch, sleeps) -> None:
    calls = script(
        monkeypatch,
        FakeResponse(
            body="User-agent: *\nDisallow: /private",
        ),
    )

    with pytest.raises(RuntimeError, match="robots.txt disallows"):
        fetch_html("https://example.com/private/x")

    assert calls == ["https://example.com/robots.txt"]


def test_missing_robots_txt_allows_fetching(monkeypatch, sleeps) -> None:
    script(
        monkeypatch,
        FakeResponse(status_code=404),
        FakeResponse(body="ok"),
    )

    assert fetch_html("https://example.com/p") == "ok"


def test_robots_txt_timeout_raises_clear_error(monkeypatch, sleeps) -> None:
    script(
        monkeypatch,
        requests.Timeout(),
    )

    with pytest.raises(RuntimeError, match="robots.txt"):
        fetch_html("https://example.com/p")
