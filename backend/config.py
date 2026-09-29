"""App settings, read once from environment variables (and .env if present)."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///data/priceunmask.db")
    scrape_target_url: str = os.getenv("SCRAPE_TARGET_URL", "")
    scrape_interval_hours: float = float(os.getenv("SCRAPE_INTERVAL_HOURS", "4"))
    scrape_user_agent: str = os.getenv("SCRAPE_USER_AGENT", "PriceUnmaskBot/0.1")
    scrape_delay_seconds: float = float(os.getenv("SCRAPE_DELAY_SECONDS", "3"))


settings = Settings()
