"""Calculate shopper-friendly price trends from price history."""

from dataclasses import dataclass

import pandas as pd

from .price_history_utils import (
    TrendDirection,
    compare_first_and_latest_prices,
    get_valid_price_history,
    validate_price_history_columns,
)


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

    validate_price_history_columns(history)

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
