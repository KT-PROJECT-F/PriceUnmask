"""Calculate shopper-friendly price trends from price history."""

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from .price_history_utils import (
    compare_first_and_latest_prices,
    get_valid_price_history,
)

TrendDirection = Literal[
    "increasing",
    "decreasing",
    "stable",
    "insufficient_history",
]


@dataclass
class PriceTrendResult:
    direction: TrendDirection
    first_price_minor: int | None
    latest_price_minor: int | None
    change_amount_minor: int | None
    change_percent: float | None
    snapshot_count: int


def calculate_price_trend(history: pd.DataFrame) -> PriceTrendResult:
    """Compare the earliest and latest valid prices."""

    required_columns = {"scraped_at", "current_price_minor"}
    missing = required_columns - set(history.columns)

    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    valid_history = get_valid_price_history(history)

    comparison = compare_first_and_latest_prices(valid_history)

    return PriceTrendResult(
        direction=comparison.direction,
        first_price_minor=comparison.first_price_minor,
        latest_price_minor=comparison.latest_price_minor,
        change_amount_minor=comparison.change_amount_minor,
        change_percent=comparison.change_percent,
        snapshot_count=len(valid_history),
    )
