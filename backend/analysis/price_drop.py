"""Detect price drops from a product's price history."""

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from .price_history_utils import (
    compare_first_and_latest_prices,
    get_valid_price_history,
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
    """Compare the first and latest valid prices using the shared 1% rule."""

    required_columns = {"scraped_at", "current_price_minor"}
    missing = required_columns - set(history.columns)

    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    valid_history = get_valid_price_history(history)

    comparison = compare_first_and_latest_prices(valid_history)

    if comparison["direction"] == "insufficient_history":
        return PriceDropResult(
            status="insufficient_history",
            previous_price_minor=None,
            current_price_minor=None,
            drop_amount_minor=None,
            drop_percent=None,
        )

    first_price = comparison["first_price_minor"]
    latest_price = comparison["latest_price_minor"]
    change_amount = comparison["change_amount_minor"]
    change_percent = comparison["change_percent"]

    if comparison["direction"] != "decreasing":
        return PriceDropResult(
            status="no_drop",
            previous_price_minor=first_price,
            current_price_minor=latest_price,
            drop_amount_minor=0,
            drop_percent=0.0,
        )

    return PriceDropResult(
        status="price_dropped",
        previous_price_minor=first_price,
        current_price_minor=latest_price,
        drop_amount_minor=abs(change_amount),
        drop_percent=abs(change_percent),
    )
