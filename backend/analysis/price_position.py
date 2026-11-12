"""Summarize the current price position against historical prices."""

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from .price_history_utils import (
    calculate_percentage,
    get_valid_price_history,
)

PricePositionStatus = Literal[
    "ok",
    "insufficient_history",
]


@dataclass
class PricePositionResult:
    status: PricePositionStatus
    lowest_price_minor: int | None
    highest_price_minor: int | None
    current_price_minor: int | None
    percent_above_lowest: float | None
    is_at_lowest: bool | None
    valid_reading_count: int


def summarize_price_position(history: pd.DataFrame) -> PricePositionResult:
    """Summarize how close the latest valid price is to the historical low."""

    required_columns = {"scraped_at", "current_price_minor"}
    missing = required_columns - set(history.columns)

    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    valid_history = get_valid_price_history(history)

    if len(valid_history) < 2:
        return PricePositionResult(
            status="insufficient_history",
            lowest_price_minor=None,
            highest_price_minor=None,
            current_price_minor=None,
            percent_above_lowest=None,
            is_at_lowest=None,
            valid_reading_count=len(valid_history),
        )

    prices = valid_history["current_price_minor"].astype(int)

    lowest_price = int(prices.min())
    highest_price = int(prices.max())
    current_price = int(prices.iloc[-1])

    percent_above_lowest = calculate_percentage(
        current_price - lowest_price,
        lowest_price,
    )

    return PricePositionResult(
        status="ok",
        lowest_price_minor=lowest_price,
        highest_price_minor=highest_price,
        current_price_minor=current_price,
        percent_above_lowest=percent_above_lowest,
        is_at_lowest=current_price == lowest_price,
        valid_reading_count=len(valid_history),
    )
