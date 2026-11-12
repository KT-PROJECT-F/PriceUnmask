import pytest

from backend.config import Settings


def test_scrape_target_urls_prefer_plural_setting_and_remove_duplicates(monkeypatch):
    monkeypatch.setenv("SCRAPE_TARGET_URLS", " https://a/,https://a/, https://b/ ")
    monkeypatch.setenv("SCRAPE_TARGET_URL", "https://legacy.example/")

    assert Settings().scrape_target_urls == ("https://a/", "https://b/")


@pytest.mark.parametrize("plural_value", [None, ""])
def test_legacy_scrape_target_url_is_used_when_plural_setting_is_unset_or_empty(
    monkeypatch, plural_value
):
    if plural_value is None:
        monkeypatch.delenv("SCRAPE_TARGET_URLS", raising=False)
    else:
        monkeypatch.setenv("SCRAPE_TARGET_URLS", plural_value)
    monkeypatch.setenv("SCRAPE_TARGET_URL", "https://legacy.example/")

    assert Settings().scrape_target_urls == ("https://legacy.example/",)
