"""Statistical anomaly pass. Owner: Analysis track (ML).

Runs ON TOP of the rules, never instead of them. Start with a rolling z-score (easy
to explain), add IsolationForest only once there is enough history to justify it.
Be honest: with 2 to 4 weeks of data this is directionally useful, not accurate.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass
class AnomalyResult:
    method: str  # "zscore" or "isolation_forest"
    anomalous_timestamps: list[str]  # ISO timestamps of flagged snapshots
    latest_is_anomalous: bool
    note: str  # e.g. "only 9 snapshots; treat as a hint"


def _rolling_zscore(prices: pd.Series, window: int = 5) -> pd.Series:
    """Calculate z-scores using only prices from earlier rows."""
    previous_prices = prices.shift(1)
    rolling_mean = previous_prices.rolling(window=window).mean()
    rolling_std = previous_prices.rolling(window=window).std()
    rolling_std = rolling_std.mask(rolling_std == 0)
    return (prices - rolling_mean) / rolling_std


def detect_anomalies(history: pd.DataFrame) -> AnomalyResult:
    raise NotImplementedError
