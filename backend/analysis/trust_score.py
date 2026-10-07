"""Rule-based Trust Score. Owner: Analysis track (rules).

Input: a history DataFrame with columns
    scraped_at (datetime, UTC), current_price_minor (int), original_price_minor (int | None)
sorted oldest first. Output: a TrustScore that EXPLAINS itself via `reasons`.

Every signal must be explainable to a shopper in one sentence. If you cannot explain
why a signal indicates a fake discount, it does not belong in the score.
"""

from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

Label = Literal["genuine", "uncertain", "likely_inflated", "insufficient_data"]

MIN_SNAPSHOTS = 6  # below this we refuse to score; say "insufficient_data" honestly


@dataclass
class TrustSignals:
    days_of_history: float
    snapshot_count: int
    lowest_price_minor: int
    pct_above_lowest: float  # today vs lowest ever, e.g. 12.5 means 12.5% above lowest
    volatility_pct: float  # coefficient of variation of price, in %
    spike_before_discount: bool  # price jumped up shortly before the current "sale"
    spike_pct: float | None
    claimed_discount_pct: float | None  # from strikethrough price, if any
    real_discount_vs_median_pct: float | None  # current vs median of prior prices


@dataclass
class TrustScore:
    score: int | None  # 0..100, None when insufficient_data
    label: Label
    signals: TrustSignals | None
    reasons: list[str] = field(default_factory=list)  # human-readable, shown in the UI


def compute_signals(history: pd.DataFrame) -> TrustSignals:
    """Compute basic Trust Score signals from price history.

    Raises:
        ValueError: If history is empty.
    """
    if history.empty:
        raise ValueError("history must contain at least one row")

    snapshot_count = len(history)

    first_time = history["scraped_at"].iloc[0]
    last_time = history["scraped_at"].iloc[-1]
    days_of_history = (last_time - first_time) / pd.Timedelta(days=1)

    lowest_price_minor = int(history["current_price_minor"].min())

    today_price = int(history["current_price_minor"].iloc[-1])

    pct_above_lowest = (today_price - lowest_price_minor) / lowest_price_minor * 100

    mean_price = history["current_price_minor"].mean()
    std_price = history["current_price_minor"].std()

    volatility_pct = (
        0.0 if mean_price == 0 or pd.isna(std_price) else (std_price / mean_price) * 100
    )

    return TrustSignals(
        days_of_history=float(days_of_history),
        snapshot_count=snapshot_count,
        lowest_price_minor=lowest_price_minor,
        pct_above_lowest=float(pct_above_lowest),
        volatility_pct=float(volatility_pct),
        spike_before_discount=False,
        spike_pct=None,
        claimed_discount_pct=None,
        real_discount_vs_median_pct=None,
    )


def compute_trust_score(history: pd.DataFrame) -> TrustScore:
    """Combine signals into 0..100. Label thresholds: >=70 genuine, 40..69 uncertain,
    <40 likely_inflated. Fewer than MIN_SNAPSHOTS rows -> insufficient_data."""
    raise NotImplementedError
