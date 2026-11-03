import logging
import re
from dataclasses import dataclass, replace

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


@dataclass(frozen=True)
class FakeProduct:
    external_id: str
    name: str = "Book"


ROBOTS_OK = FakeResponse(
    body="User-agent: *\nAllow: /",
)


def test_configured_delay_between_robots_and_page(
    monkeypatch,
    sleeps,
) -> None:
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


def test_robots_txt_timeout_retries_then_succeeds(monkeypatch, sleeps):
    calls = script(
        monkeypatch,
        requests.Timeout(),
        ROBOTS_OK,
        FakeResponse(body="ok"),
    )

    assert fetch_html("https://example.com/products") == "ok"

    assert calls == [
        "https://example.com/robots.txt",
        "https://example.com/robots.txt",
        "https://example.com/products",
    ]
    assert sleeps == [1, settings.scrape_delay_seconds]


def test_robots_txt_timeout_on_every_attempt_fails_without_requesting_page(
    monkeypatch,
    sleeps,
) -> None:
    calls = script(
        monkeypatch,
        requests.Timeout(),
        requests.Timeout(),
        requests.Timeout(),
    )

    with pytest.raises(
        RuntimeError,
        match="Could not fetch robots.txt",
    ):
        fetch_html("https://example.com/products")

    assert calls == [
        "https://example.com/robots.txt",
        "https://example.com/robots.txt",
        "https://example.com/robots.txt",
    ]

    assert sleeps == [1, 2]


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
    expected_products = [
        FakeProduct("product-1"),
        FakeProduct("product-2"),
    ]
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
        lambda html, base_url: [FakeProduct("product")],
    )

    assert product_scraper.scrape("https://example.com/list") == [FakeProduct("product")]


def test_fetch_html_logs_robots_user_agent_and_delay(
    monkeypatch,
    caplog,
) -> None:
    script(monkeypatch, ROBOTS_OK, FakeResponse(body="ok"))

    with caplog.at_level(
        logging.INFO,
        logger="backend.scraper.product_scraper",
    ):
        fetch_html("https://example.com/p")

    assert "Checking robots.txt: https://example.com/robots.txt" in caplog.text
    assert f"Using User-Agent: {settings.scrape_user_agent}" in caplog.text
    assert f"Waiting {settings.scrape_delay_seconds:.2f} seconds" in caplog.text
    assert "Fetched https://example.com/p: HTTP 200" in caplog.text


def test_fetch_html_logs_each_retry(monkeypatch, caplog) -> None:
    script(
        monkeypatch,
        ROBOTS_OK,
        FakeResponse(503),
        FakeResponse(503),
        FakeResponse(body="ok"),
    )

    with caplog.at_level(
        logging.WARNING,
        logger="backend.scraper.product_scraper",
    ):
        fetch_html("https://example.com/p")

    assert "retry 1 of 2" in caplog.text
    assert "retry 2 of 2" in caplog.text


def test_external_redirect_is_rejected(monkeypatch, sleeps) -> None:
    redirect = FakeResponse(status_code=302)
    redirect.headers["Location"] = "https://other.example/page"

    calls = script(monkeypatch, ROBOTS_OK, redirect)

    with pytest.raises(RuntimeError, match="Redirect not followed"):
        fetch_html("https://example.com/page")

    assert calls == [
        "https://example.com/robots.txt",
        "https://example.com/page",
    ]
    assert sleeps == [settings.scrape_delay_seconds]


def test_same_site_redirect_is_rejected(monkeypatch, sleeps) -> None:
    redirect = FakeResponse(status_code=301)
    redirect.headers["Location"] = "/page/"

    calls = script(monkeypatch, ROBOTS_OK, redirect)

    with pytest.raises(RuntimeError, match="Redirect not followed"):
        fetch_html("https://example.com/page")

    assert len(calls) == 2


def test_redirect_without_location_is_rejected(monkeypatch, sleeps) -> None:
    calls = script(
        monkeypatch,
        ROBOTS_OK,
        FakeResponse(status_code=302),
    )

    with pytest.raises(RuntimeError, match="no Location header"):
        fetch_html("https://example.com/page")

    assert len(calls) == 2


def test_redirect_is_not_retried(monkeypatch, sleeps) -> None:
    calls = script(
        monkeypatch,
        ROBOTS_OK,
        FakeResponse(status_code=307),
    )

    with pytest.raises(RuntimeError):
        fetch_html("https://example.com/page")

    assert len(calls) == 2
    assert sleeps == [settings.scrape_delay_seconds]


def test_robots_txt_redirect_stops_before_the_page(
    monkeypatch,
    sleeps,
) -> None:
    calls = script(
        monkeypatch,
        FakeResponse(status_code=301),
    )

    with pytest.raises(RuntimeError, match="robots.txt redirected"):
        fetch_html("https://example.com/page")

    assert calls == ["https://example.com/robots.txt"]
    assert sleeps == []


def test_non_html_response_is_rejected(monkeypatch, sleeps) -> None:
    calls = script(
        monkeypatch,
        ROBOTS_OK,
        FakeResponse(
            body="%PDF-1.7",
            content_type="application/pdf",
        ),
    )

    with pytest.raises(RuntimeError, match="Expected HTML"):
        fetch_html("https://example.com/document")

    assert len(calls) == 2


def test_missing_content_type_is_rejected(monkeypatch, sleeps) -> None:
    script(
        monkeypatch,
        ROBOTS_OK,
        FakeResponse(
            body="<html></html>",
            content_type="",
        ),
    )

    with pytest.raises(RuntimeError, match="no Content-Type"):
        fetch_html("https://example.com/page")


def test_disallowed_url_is_logged_once(monkeypatch, caplog) -> None:
    script(
        monkeypatch,
        FakeResponse(
            body="User-agent: *\nDisallow: /private",
        ),
    )

    with (
        caplog.at_level(
            logging.WARNING,
            logger="backend.scraper.product_scraper",
        ),
        pytest.raises(RuntimeError),
    ):
        fetch_html("https://example.com/private/x")

    assert caplog.text.count("robots.txt disallows") == 1


# ---------------------------------------------------------------------
# Pagination tests
# ---------------------------------------------------------------------


def use_pages(monkeypatch, tmp_path, pages, *, max_pages=3):
    """Fake fetch_html with a dict of URL -> HTML, and return fetched URLs."""

    calls = []

    def fake_fetch(url):
        calls.append(url)
        page = pages[url]

        if isinstance(page, Exception):
            raise page

        return page

    monkeypatch.setattr(product_scraper, "SNAPSHOT_DIR", tmp_path)
    monkeypatch.setattr(product_scraper, "fetch_html", fake_fetch)
    monkeypatch.setattr(
        product_scraper,
        "settings",
        replace(settings, scrape_max_pages=max_pages),
    )

    return calls


def next_link(href):
    return f'<ul class="pager"><li class="next"><a href="{href}">next</a></li></ul>'


PAGE_1 = "https://example.com/catalogue/page-1.html"
PAGE_2 = "https://example.com/catalogue/page-2.html"
PAGE_3 = "https://example.com/catalogue/page-3.html"


def test_scrape_follows_next_page(monkeypatch, tmp_path):
    calls = use_pages(
        monkeypatch,
        tmp_path,
        {
            PAGE_1: next_link("page-2.html"),
            PAGE_2: "<html></html>",
        },
    )

    monkeypatch.setattr(
        product_scraper,
        "parse_listing",
        lambda html, url: [FakeProduct("book1")] if url == PAGE_1 else [FakeProduct("book2")],
    )

    products = product_scraper.scrape(PAGE_1)

    assert calls == [PAGE_1, PAGE_2]
    assert [product.external_id for product in products] == [
        "book1",
        "book2",
    ]
    assert len(list(tmp_path.glob("*.html"))) == 2


def test_scrape_stops_when_no_next_page(monkeypatch, tmp_path):
    calls = use_pages(
        monkeypatch,
        tmp_path,
        {PAGE_1: "<html></html>"},
    )

    monkeypatch.setattr(
        product_scraper,
        "parse_listing",
        lambda html, url: [],
    )

    assert product_scraper.scrape(PAGE_1) == []
    assert calls == [PAGE_1]


def test_scrape_respects_max_pages(monkeypatch, tmp_path):
    pages = {
        PAGE_1: next_link("page-2.html"),
        PAGE_2: next_link("page-3.html"),
        PAGE_3: "",
    }

    calls = use_pages(
        monkeypatch,
        tmp_path,
        pages,
        max_pages=2,
    )

    monkeypatch.setattr(
        product_scraper,
        "parse_listing",
        lambda html, url: [],
    )

    product_scraper.scrape(PAGE_1)

    assert calls == [PAGE_1, PAGE_2]
    assert len(list(tmp_path.glob("*.html"))) == 2


def test_scrape_returns_a_book_on_two_pages_once(monkeypatch, tmp_path):
    use_pages(
        monkeypatch,
        tmp_path,
        {
            PAGE_1: next_link("page-2.html"),
            PAGE_2: "",
        },
    )

    monkeypatch.setattr(
        product_scraper,
        "parse_listing",
        lambda html, url: (
            [FakeProduct("book1"), FakeProduct("book2")]
            if url == PAGE_1
            else [
                FakeProduct("book2", "Book 2 again"),
                FakeProduct("book3"),
            ]
        ),
    )

    products = product_scraper.scrape(PAGE_1)

    assert [product.external_id for product in products] == [
        "book1",
        "book2",
        "book3",
    ]
    assert products[1].name == "Book"


def test_scrape_stops_when_pages_link_to_each_other(monkeypatch, tmp_path):
    pages = {
        PAGE_1: next_link("page-2.html"),
        PAGE_2: next_link("page-1.html"),
    }

    calls = use_pages(monkeypatch, tmp_path, pages)

    monkeypatch.setattr(
        product_scraper,
        "parse_listing",
        lambda html, url: [],
    )

    product_scraper.scrape(PAGE_1)

    assert calls == [PAGE_1, PAGE_2]


def test_scrape_raises_when_a_middle_page_fails(monkeypatch, tmp_path):
    pages = {
        PAGE_1: next_link("page-2.html"),
        PAGE_2: RuntimeError("page 2 failed"),
    }

    calls = use_pages(monkeypatch, tmp_path, pages)

    monkeypatch.setattr(
        product_scraper,
        "parse_listing",
        lambda html, url: [FakeProduct("book1")],
    )

    with pytest.raises(RuntimeError, match="page 2 failed"):
        product_scraper.scrape(PAGE_1)

    assert calls == [PAGE_1, PAGE_2]

    # Page 1's raw HTML is kept even though the run fails.
    [snapshot] = list(tmp_path.glob("*.html"))
    assert re.fullmatch(r"\d{8}T\d{6}Z\.html", snapshot.name)


def test_scrape_names_later_pages_with_a_page_number(monkeypatch, tmp_path):
    use_pages(
        monkeypatch,
        tmp_path,
        {
            PAGE_1: next_link("page-2.html"),
            PAGE_2: "",
        },
    )

    monkeypatch.setattr(
        product_scraper,
        "parse_listing",
        lambda html, url: [],
    )

    product_scraper.scrape(PAGE_1)

    names = sorted(path.name for path in tmp_path.glob("*.html"))

    assert re.fullmatch(r"\d{8}T\d{6}Z\.html", names[0])
    assert re.fullmatch(r"\d{8}T\d{6}Z_page2\.html", names[1])
