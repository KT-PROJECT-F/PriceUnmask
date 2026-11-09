
"""Detect price drops from a product's price history."""

from dataclasses import dataclass
from typing import Literal

import pandas as pd

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
    """Compare the latest price with the immediately previous observed price."""

    required_columns = {"scraped_at", "current_price_minor"}
    missing = required_columns - set(history.columns)

    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    valid_history = history.dropna(subset=["scraped_at", "current_price_minor"]).copy()

    if len(valid_history) < 2:
        return PriceDropResult(
            status="insufficient_history",
            previous_price_minor=None,
            current_price_minor=None,
            drop_amount_minor=None,
            drop_percent=None,
        )

    valid_history = valid_history.sort_values("scraped_at")

    previous_price = int(valid_history.iloc[-2]["current_price_minor"])
    current_price = int(valid_history.iloc[-1]["current_price_minor"])

    if previous_price <= 0 or current_price < 0:
        raise ValueError(
            "Prices must be non-negative and previous price must be greater than zero."
        )

    if current_price >= previous_price:
        return PriceDropResult(
            status="no_drop",
            previous_price_minor=previous_price,
            current_price_minor=current_price,
            drop_amount_minor=0,
            drop_percent=0.0,
        )

    drop_amount = previous_price - current_price
    drop_percent = (drop_amount / previous_price) * 100

    return PriceDropResult(
        status="price_dropped",
        previous_price_minor=previous_price,
        current_price_minor=current_price,
        drop_amount_minor=drop_amount,
        drop_percent=round(drop_percent, 2),
    )
