"""Calculate shopper-friendly price trends from price history."""

from dataclasses import dataclass
from typing import Literal

import pandas as pd

TrendDirection = Literal["increasing", "decreasing", "stable", "insufficient_history"]


@dataclass
class PriceTrendResult:
    direction: TrendDirection
    first_price_minor: int | None
    latest_price_minor: int | None
    change_amount_minor: int | None
    change_percent: float | None
    snapshot_count: int


def calculate_price_trend(history: pd.DataFrame) -> PriceTrendResult:
    """Compare the earliest and latest observed prices."""

    required_columns = {"scraped_at", "current_price_minor"}
    missing = required_columns - set(history.columns)

    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    valid_history = history.dropna(subset=["scraped_at", "current_price_minor"]).copy()

    if len(valid_history) < 2:
        return PriceTrendResult(
            direction="insufficient_history",
            first_price_minor=None,
            latest_price_minor=None,
            change_amount_minor=None,
            change_percent=None,
            snapshot_count=len(valid_history),
        )

    valid_history = valid_history.sort_values("scraped_at")

    first_price = int(valid_history.iloc[0]["current_price_minor"])
    latest_price = int(valid_history.iloc[-1]["current_price_minor"])

    if first_price <= 0 or latest_price < 0:
        raise ValueError("Prices must be non-negative and first price must be greater than zero.")

    change_amount = latest_price - first_price
    change_percent = (change_amount / first_price) * 100

    if change_amount > 0:
        direction = "increasing"
    elif change_amount < 0:
        direction = "decreasing"
    else:
        direction = "stable"

    return PriceTrendResult(
        direction=direction,
        first_price_minor=first_price,
        latest_price_minor=latest_price,
        change_amount_minor=change_amount,
        change_percent=round(change_percent, 2),
        snapshot_count=len(valid_history),
    )
