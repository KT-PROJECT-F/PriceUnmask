"""Statistical anomaly pass. Owner: Analysis track (ML).

Runs ON TOP of the rules, never instead of them. Start with a rolling z-score (easy
to explain), add IsolationForest only once there is enough history to justify it.
Be honest: with 2 to 4 weeks of data this is directionally useful, not accurate.
"""

from dataclasses import dataclass

import pandas as pd

ROLLING_WINDOW = 5
ZSCORE_THRESHOLD = 3.0


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
    """Flag unusual prices using each row's five immediately preceding prices.

    Rows before the sixth snapshot cannot be scored because they lack a complete
    prior window. A zero-standard-deviation window has no z-score; a price that
    differs from that flat baseline is flagged as a departure. Otherwise, rows
    with an absolute z-score of at least 3 are flagged. Timestamps are returned
    in chronological order as UTC ISO strings.
    """
    if history.empty:
        return AnomalyResult(
            method="zscore",
            anomalous_timestamps=[],
            latest_is_anomalous=False,
            note="No snapshots are available.",
        )

    required_columns = {"scraped_at", "current_price_minor"}
    missing_columns = required_columns - set(history.columns)
    if missing_columns:
        raise ValueError(f"history is missing required columns: {sorted(missing_columns)}")

    ordered_history = history.assign(
        scraped_at=pd.to_datetime(history["scraped_at"], utc=True)
    ).sort_values("scraped_at", kind="stable", ignore_index=True)

    if len(ordered_history) <= ROLLING_WINDOW:
        return AnomalyResult(
            method="zscore",
            anomalous_timestamps=[],
            latest_is_anomalous=False,
            note=(
                f"Only {len(ordered_history)} snapshots; at least "
                f"{ROLLING_WINDOW + 1} are needed to score a price."
            ),
        )

    z_scores = _rolling_zscore(
        ordered_history["current_price_minor"],
        window=ROLLING_WINDOW,
    )
    prices = ordered_history["current_price_minor"]
    previous_prices = prices.shift(1)
    previous_mean = previous_prices.rolling(window=ROLLING_WINDOW).mean()
    previous_std = previous_prices.rolling(window=ROLLING_WINDOW).std()
    departed_from_flat_baseline = previous_std.eq(0) & prices.ne(previous_mean)
    flagged = z_scores.abs().ge(ZSCORE_THRESHOLD).fillna(False) | departed_from_flat_baseline
    anomalous_timestamps = [
        timestamp.isoformat().replace("+00:00", "Z")
        for timestamp in ordered_history.loc[flagged, "scraped_at"]
    ]

    if anomalous_timestamps:
        note = (
            f"Flagged {len(anomalous_timestamps)} snapshot(s) with "
            f"|z| >= {ZSCORE_THRESHOLD} or a departure from a flat "
            f"{ROLLING_WINDOW}-price baseline."
        )
    else:
        note = (
            f"No rolling z-score reached |z| >= {ZSCORE_THRESHOLD}; "
            "zero-standard-deviation windows have no score."
        )

    return AnomalyResult(
        method="zscore",
        anomalous_timestamps=anomalous_timestamps,
        latest_is_anomalous=bool(flagged.iloc[-1]),
        note=note,
    )
