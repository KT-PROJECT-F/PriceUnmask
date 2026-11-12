"""Detect price drops from a product's price history."""

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from .price_history_utils import (
    STABLE_THRESHOLD_PCT,
    calculate_percentage,
    get_valid_price_history,
    validate_price_history_columns,
)

PriceDropStatus = Literal[
    "insufficient_history",
    "price_dropped",
    "no_drop",
]


@dataclass
class PriceDropResult:
    status: PriceDropStatus
    previous_price_minor: int | None
    current_price_minor: int | None
    drop_amount_minor: int | None
    drop_percent: float | None


def detect_price_drop(history: pd.DataFrame) -> PriceDropResult:
    """
    Compare the latest price with the start of its latest falling stretch.

    Equal readings are included in the falling stretch.
    If the latest price increased, use the immediately previous valid
    reading as the previous price.

    Percentages are rounded to two decimals before threshold comparison.
    """

    validate_price_history_columns(history)

    valid_history = get_valid_price_history(history)

    if len(valid_history) < 2:
        return PriceDropResult(
            status="insufficient_history",
            previous_price_minor=None,
            current_price_minor=None,
            drop_amount_minor=None,
            drop_percent=None,
        )

    prices = valid_history["current_price_minor"].tolist()
    current_price = int(prices[-1])

    previous_index = len(prices) - 2

    # If the latest price did not increase, find the start
    # of the latest falling stretch, including equal readings.
    if prices[-1] <= prices[-2]:
        while previous_index > 0 and prices[previous_index - 1] >= prices[previous_index]:
            previous_index -= 1

    previous_price = int(prices[previous_index])

    change_amount = previous_price - current_price

    change_percent = calculate_percentage(change_amount, previous_price)

    if change_percent < STABLE_THRESHOLD_PCT:
        return PriceDropResult(
            status="no_drop",
            previous_price_minor=previous_price,
            current_price_minor=current_price,
            drop_amount_minor=0,
            drop_percent=0.0,
        )

    return PriceDropResult(
        status="price_dropped",
        previous_price_minor=previous_price,
        current_price_minor=current_price,
        drop_amount_minor=change_amount,
        drop_percent=change_percent,
    )
