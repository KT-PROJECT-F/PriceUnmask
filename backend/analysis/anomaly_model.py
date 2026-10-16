"""Statistical anomaly pass. Owner: Analysis track (ML).

Runs ON TOP of the rules, never instead of them. Start with a rolling z-score (easy
to explain), add IsolationForest only once there is enough history to justify it.
Be honest: with 2 to 4 weeks of data this is directionally useful, not accurate.
"""

from dataclasses import dataclass

import pandas as pd

ROLLING_WINDOW = 5
ZSCORE_THRESHOLD = 3.0
MIN_CHANGE_PERCENT = 10.0


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
    """Flag unusual prices using the five immediately preceding prices.

    Rows before the sixth snapshot cannot be scored because they lack a complete
    prior window. Changes of at least 10% from a flat baseline are flagged.
    For non-flat baselines, a change must be at least 10% and have an absolute
    z-score of at least 3. Timestamps are returned in chronological order as
    UTC ISO strings.
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

    prices = ordered_history["current_price_minor"]
    previous_prices = prices.shift(1)
    previous_mean = previous_prices.rolling(window=ROLLING_WINDOW).mean()
    previous_std = previous_prices.rolling(window=ROLLING_WINDOW).std()

    z_scores = _rolling_zscore(prices, window=ROLLING_WINDOW)

    # Compare each price with the average of its five preceding prices.
    # Example: 2000 vs 1000 is a 100% change, so flag it.
    # 1001 vs 1000 is a 0.1% change, so do not flag it.
    # 1030 vs 1000 is a 3% change, so do not flag it.
    percentage_change = ((prices - previous_mean).abs() / previous_mean.abs()) * 100

    has_complete_window = previous_prices.rolling(window=ROLLING_WINDOW).count().eq(ROLLING_WINDOW)

    flat_baseline = previous_std.eq(0)
    large_enough_change = percentage_change.ge(MIN_CHANGE_PERCENT)

    # After a flat baseline, use the 10% rule.
    # Otherwise, require both z-score >= 3 and a change >= 10%.
    flagged = (
        has_complete_window
        & large_enough_change
        & (flat_baseline | z_scores.abs().ge(ZSCORE_THRESHOLD))
    ).fillna(False)

    anomalous_timestamps = [
        timestamp.isoformat().replace("+00:00", "Z")
        for timestamp in ordered_history.loc[flagged, "scraped_at"]
    ]

    if anomalous_timestamps:
        note = (
            f"Flagged {len(anomalous_timestamps)} snapshot(s) with "
            f"a change of at least {MIN_CHANGE_PERCENT}% and, "
            f"for non-flat baselines, |z| >= {ZSCORE_THRESHOLD}."
        )
    else:
        note = (
            f"No price change met the {MIN_CHANGE_PERCENT}% threshold "
            "and the applicable anomaly rule."
        )

    return AnomalyResult(
        method="zscore",
        anomalous_timestamps=anomalous_timestamps,
        latest_is_anomalous=bool(flagged.iloc[-1]),
        note=note,
    )
