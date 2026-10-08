import re

import pytest
import requests

from backend.config import settings
from backend.scraper import product_scraper
from backend.scraper.product_scraper import FETCH_TIMEOUT_SECONDS, fetch_html


class FakeResponse:
    """Behaves like requests: no charset -> ISO-8859-1."""

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


def use_fake(
    monkeypatch,
    response: FakeResponse,
    calls: list | None = None,
) -> None:
    def fake_get(url, **kwargs):
        if calls is not None:
            calls.append((url, kwargs))
        return response

    monkeypatch.setattr(
        "backend.scraper.product_scraper.requests.get",
        fake_get,
    )


@pytest.fixture(autouse=True)
def sleeps(monkeypatch):
    waits: list[float] = []
    monkeypatch.setattr(
        "backend.scraper.product_scraper.sleep",
        waits.append,
    )
    return waits


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


def test_pound_sign_survives_without_charset(monkeypatch) -> None:
    responses = [
        FakeResponse(
            body="User-agent: *\nAllow: /",
        ),
        FakeResponse(
            body="<p>£51.77</p>",
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


def script(monkeypatch, *steps):
    """Return or raise each step in order for requests.get."""
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


def test_configured_delay_between_robots_and_page(monkeypatch, sleeps) -> None:
    calls: list[str] = []
    queue = [
        ROBOTS_OK,
        FakeResponse(body="ok"),
    ]

    def fake_get(url, **kwargs):
        calls.append(url)
        return queue.pop(0)

    monkeypatch.setattr(
        "backend.scraper.product_scraper.requests.get",
        fake_get,
    )
    delay = settings.scrape_delay_seconds
    fetch_html("https://example.com/p")
    assert calls == [
        "https://example.com/robots.txt",
        "https://example.com/p",
    ]
    assert sleeps == [delay]


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
    assert sleeps == [settings.scrape_delay_seconds, 1, 2]


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
    assert sleeps == [settings.scrape_delay_seconds, 1, 2]


def test_404_is_not_retried(monkeypatch, sleeps) -> None:
    calls = script(
        monkeypatch,
        ROBOTS_OK,
        FakeResponse(404),
    )
    with pytest.raises(RuntimeError, match="HTTP 404"):
        fetch_html("https://example.com/p")
    assert len(calls) == 2
    assert sleeps == [settings.scrape_delay_seconds]


@pytest.mark.parametrize("status", [500, 502, 503, 504])
def test_temporary_status_is_retried_then_raises(
    monkeypatch,
    sleeps,
    status: int,
) -> None:
    calls = script(
        monkeypatch,
        ROBOTS_OK,
        FakeResponse(status),
        FakeResponse(status),
        FakeResponse(status),
    )
    with pytest.raises(RuntimeError, match=f"HTTP {status}"):
        fetch_html("https://example.com/p")
    assert len(calls) == 4
    assert sleeps == [settings.scrape_delay_seconds, 1, 2]


def test_timeout_is_retried(monkeypatch, sleeps) -> None:
    script(
        monkeypatch,
        ROBOTS_OK,
        requests.Timeout(),
        FakeResponse(body="ok"),
    )
    assert fetch_html("https://example.com/p") == "ok"
    assert sleeps == [settings.scrape_delay_seconds, 1]


def test_connection_error_is_retried(monkeypatch, sleeps) -> None:
    script(
        monkeypatch,
        ROBOTS_OK,
        requests.ConnectionError(),
        FakeResponse(body="ok"),
    )
    assert fetch_html("https://example.com/p") == "ok"
    assert sleeps == [settings.scrape_delay_seconds, 1]


def test_timeout_on_every_attempt_raises_after_three_tries(
    monkeypatch,
    sleeps,
) -> None:
    calls = script(
        monkeypatch,
        ROBOTS_OK,
        requests.Timeout(),
        requests.Timeout(),
        requests.Timeout(),
    )
    with pytest.raises(requests.Timeout):
        fetch_html("https://example.com/p")
    assert len(calls) == 4
    assert sleeps == [settings.scrape_delay_seconds, 1, 2]


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
    assert sleeps == []


def test_missing_robots_txt_allows_fetching(monkeypatch, sleeps) -> None:
    script(
        monkeypatch,
        FakeResponse(status_code=404),
        FakeResponse(body="ok"),
    )
    assert fetch_html("https://example.com/p") == "ok"
    assert sleeps == [settings.scrape_delay_seconds]


def test_robots_txt_timeout_raises_clear_error(monkeypatch, sleeps) -> None:
    script(
        monkeypatch,
        requests.Timeout(),
    )
    with pytest.raises(RuntimeError, match="robots.txt"):
        fetch_html("https://example.com/p")
    assert sleeps == []


@pytest.mark.parametrize("status", [403, 500])
def test_robots_txt_error_status_raises_and_page_is_not_requested(
    monkeypatch,
    sleeps,
    status: int,
) -> None:
    calls = script(
        monkeypatch,
        FakeResponse(status_code=status),
    )
    with pytest.raises(
        RuntimeError,
        match=f"robots.txt returned HTTP {status}",
    ):
        fetch_html("https://example.com/p")
    assert calls == ["https://example.com/robots.txt"]
    assert sleeps == []


def test_scrape_saves_raw_html(monkeypatch, tmp_path) -> None:
    html = "<html><body>saved page</body></html>"
    seen = {}
    monkeypatch.setattr(product_scraper, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(product_scraper, "fetch_html", lambda url: html)

    def fake_parse(page_html, base_url):
        seen["html"] = page_html
        seen["url"] = base_url
        return []

    monkeypatch.setattr(product_scraper, "parse_listing", fake_parse)
    product_scraper.scrape("https://example.com/list")

    [snapshot] = list(tmp_path.glob("*.html"))
    assert re.fullmatch(r"\d{8}T\d{6}Z\.html", snapshot.name)
    assert snapshot.read_text(encoding="utf-8") == html
    assert seen == {
        "html": html,
        "url": "https://example.com/list",
    }


def test_scrape_returns_parsed_products(monkeypatch, tmp_path) -> None:
    html = "<html>test</html>"
    expected_products = ["product-1", "product-2"]
    seen = {}
    monkeypatch.setattr(product_scraper, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(product_scraper, "fetch_html", lambda url: html)

    def fake_parse(page_html, base_url):
        seen["html"] = page_html
        seen["url"] = base_url
        return expected_products

    monkeypatch.setattr(product_scraper, "parse_listing", fake_parse)
    result = product_scraper.scrape("https://example.com/list")
    assert result == expected_products
    assert seen == {
        "html": html,
        "url": "https://example.com/list",
    }


def test_scrape_does_not_save_when_fetch_fails(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(product_scraper, "SNAPSHOT_DIR", tmp_path)

    def fail_fetch(url):
        raise RuntimeError("fetch failed")

    monkeypatch.setattr(product_scraper, "fetch_html", fail_fetch)
    with pytest.raises(RuntimeError, match="fetch failed"):
        product_scraper.scrape("https://example.com")
    assert list(tmp_path.iterdir()) == []


def test_scrape_saves_the_page_even_if_the_parser_crashes(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(product_scraper, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(
        product_scraper,
        "fetch_html",
        lambda url: "<html>x</html>",
    )

    def broken_parse(html, base_url):
        raise ValueError("parser bug")

    monkeypatch.setattr(product_scraper, "parse_listing", broken_parse)

    with pytest.raises(ValueError, match="parser bug"):
        product_scraper.scrape("https://example.com/list")

    assert len(list(tmp_path.glob("*.html"))) == 1


def test_scrape_returns_products_when_the_snapshot_cannot_be_saved(
    monkeypatch,
    tmp_path,
) -> None:
    blocker = tmp_path / "not-a-folder"
    blocker.write_text("x")

    monkeypatch.setattr(
        product_scraper,
        "SNAPSHOT_DIR",
        blocker / "snapshots",
    )
    monkeypatch.setattr(
        product_scraper,
        "fetch_html",
        lambda url: "<html>x</html>",
    )
    monkeypatch.setattr(
        product_scraper,
        "parse_listing",
        lambda html, base_url: ["product"],
    )

    assert product_scraper.scrape("https://example.com/list") == ["product"]
