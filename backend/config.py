"""App settings, read once from environment variables (and .env if present)."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _get_scrape_target_urls() -> tuple[str, ...]:
    configured_urls = os.getenv("SCRAPE_TARGET_URLS")
    if not configured_urls:
        configured_urls = os.getenv("SCRAPE_TARGET_URL", "")

    return tuple(dict.fromkeys(url.strip() for url in configured_urls.split(",") if url.strip()))


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///data/priceunmask.db")
    scrape_target_urls: tuple[str, ...] = field(default_factory=_get_scrape_target_urls)
    scrape_interval_hours: float = float(os.getenv("SCRAPE_INTERVAL_HOURS", "4"))
    scrape_user_agent: str = os.getenv(
        "SCRAPE_USER_AGENT",
        "PriceUnmaskBot/0.1 (learning project; contact: you@example.com)",
    )
    scrape_delay_seconds: float = float(os.getenv("SCRAPE_DELAY_SECONDS", "3"))
    scrape_max_pages: int = int(os.getenv("SCRAPE_MAX_PAGES", "3"))
    stale_run_minutes: int = int(os.getenv("STALE_RUN_MINUTES", "30"))


settings = Settings()
