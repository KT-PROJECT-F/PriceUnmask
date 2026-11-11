from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

STABLE_THRESHOLD_PCT = 1.0

TrendDirection = Literal[
    "increasing",
    "decreasing",
    "stable",
    "insufficient_history",
]


@dataclass
class PriceComparisonResult:
    first_price_minor: int | None
    latest_price_minor: int | None
    change_amount_minor: int | None
    change_percent: float | None
    direction: TrendDirection


def get_valid_price_history(history: pd.DataFrame) -> pd.DataFrame:
    """
    Return price history containing only valid price records.

    Invalid dates, non-numeric prices, non-finite prices,
    zero prices, negative prices, and fractional prices are skipped.
    """

    if history.empty:
        return history.copy()

    required_columns = {"scraped_at", "current_price_minor"}

    if not required_columns.issubset(history.columns):
        return history.iloc[0:0].copy()

    valid_history = history.copy()

    valid_history["current_price_minor"] = pd.to_numeric(
        valid_history["current_price_minor"],
        errors="coerce",
    )

    valid_history["scraped_at"] = pd.to_datetime(
        valid_history["scraped_at"],
        errors="coerce",
        utc=True,
    )

    valid_history = valid_history.dropna(subset=["scraped_at", "current_price_minor"])

    prices = valid_history["current_price_minor"]

    valid_history = valid_history[np.isfinite(prices) & (prices > 0) & (prices % 1 == 0)]

    valid_history = valid_history.sort_values(
        "scraped_at",
        kind="stable",
        ignore_index=True,
    )

    return valid_history


def compare_first_and_latest_prices(
    valid_history: pd.DataFrame,
) -> PriceComparisonResult:
    """
    Compare the first and latest valid prices using a 1% threshold.

    Changes below 1% are stable.
    Changes at or above 1% are increasing or decreasing.
    """

    if len(valid_history) < 2:
        return PriceComparisonResult(
            first_price_minor=None,
            latest_price_minor=None,
            change_amount_minor=None,
            change_percent=None,
            direction="insufficient_history",
        )

    first_price = int(valid_history.iloc[0]["current_price_minor"])
    latest_price = int(valid_history.iloc[-1]["current_price_minor"])

    change_amount = latest_price - first_price
    change_percent = change_amount / first_price * 100

    if abs(change_percent) < STABLE_THRESHOLD_PCT:
        direction = "stable"
    elif change_amount > 0:
        direction = "increasing"
    else:
        direction = "decreasing"

    return PriceComparisonResult(
        first_price_minor=first_price,
        latest_price_minor=latest_price,
        change_amount_minor=change_amount,
        change_percent=round(change_percent, 2),
        direction=direction,
    )
