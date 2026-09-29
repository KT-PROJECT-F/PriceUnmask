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
    raise NotImplementedError


def compute_trust_score(history: pd.DataFrame) -> TrustScore:
    """Combine signals into 0..100. Label thresholds: >=70 genuine, 40..69 uncertain,
    <40 likely_inflated. Fewer than MIN_SNAPSHOTS rows -> insufficient_data."""
    raise NotImplementedError
