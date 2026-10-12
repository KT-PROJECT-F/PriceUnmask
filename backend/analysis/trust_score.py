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
SPIKE_WINDOW_DAYS = 7
SPIKE_THRESHOLD_PCT = 50.0

SPIKE_PENALTY = 40
LARGE_DISCOUNT_GAP_THRESHOLD_PCT = 30.0
LARGE_DISCOUNT_GAP_PENALTY = 25
MODERATE_DISCOUNT_GAP_THRESHOLD_PCT = 15.0
MODERATE_DISCOUNT_GAP_PENALTY = 10
PRICE_ABOVE_LOWEST_THRESHOLD_PCT = 25.0
PRICE_ABOVE_LOWEST_PENALTY = 15
HIGH_VOLATILITY_THRESHOLD_PCT = 30.0
HIGH_VOLATILITY_PENALTY = 15


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

    prices = history["current_price_minor"]
    today_price = int(prices.iloc[-1])

    # A price of 0 would divide by zero; there is no meaningful "% above" a free price.
    pct_above_lowest = (
        (today_price - lowest_price_minor) / lowest_price_minor * 100
        if lowest_price_minor > 0
        else 0.0
    )

    mean_price = prices.mean()
    std_price = prices.std()

    volatility_pct = (
        0.0 if mean_price == 0 or pd.isna(std_price) else (std_price / mean_price) * 100
    )

    latest_original_price = history["original_price_minor"].iloc[-1]
    claimed_discount_pct = (
        float((latest_original_price - today_price) / latest_original_price * 100)
        if pd.notna(latest_original_price)
        and latest_original_price >= today_price
        and latest_original_price > 0
        else None
    )

    prior_median = prices.iloc[:-1].median()
    real_discount_vs_median_pct = (
        max(0.0, float((prior_median - today_price) / prior_median * 100))
        if pd.notna(prior_median) and prior_median > 0
        else None
    )

    timestamps = history["scraped_at"]
    claimed_sale = (
        history["original_price_minor"].notna()
        & (history["original_price_minor"] > prices)
        & (history["original_price_minor"] > 0)
    )
    sale_start_index = snapshot_count - 1
    while sale_start_index > 0 and claimed_sale.iloc[sale_start_index - 1]:
        sale_start_index -= 1
    sale_start_time = timestamps.iloc[sale_start_index]
    spike_cutoff = sale_start_time - pd.Timedelta(days=SPIKE_WINDOW_DAYS)
    baseline_prices = prices.loc[timestamps < spike_cutoff]
    recent_prices = prices.loc[(timestamps >= spike_cutoff) & (timestamps < sale_start_time)]
    if baseline_prices.empty or recent_prices.empty:
        # We need both an older baseline and pre-sale prices to measure a spike.
        spike_pct = None
    else:
        baseline_median = baseline_prices.median()
        spike_pct = (
            float((recent_prices.max() - baseline_median) / baseline_median * 100)
            if baseline_median > 0
            else None
        )
    spike_before_discount = (
        claimed_discount_pct is not None
        and claimed_discount_pct > 0
        and spike_pct is not None
        and spike_pct >= SPIKE_THRESHOLD_PCT
    )

    return TrustSignals(
        days_of_history=float(days_of_history),
        snapshot_count=snapshot_count,
        lowest_price_minor=lowest_price_minor,
        pct_above_lowest=float(pct_above_lowest),
        volatility_pct=float(volatility_pct),
        spike_before_discount=spike_before_discount,
        spike_pct=spike_pct,
        claimed_discount_pct=claimed_discount_pct,
        real_discount_vs_median_pct=real_discount_vs_median_pct,
    )


def compute_trust_score(history: pd.DataFrame) -> TrustScore:
    """Combine signals into 0..100. Label thresholds: >=70 genuine, 40..69 uncertain,
    <40 likely_inflated. Fewer than MIN_SNAPSHOTS rows -> insufficient_data."""
    snapshot_count = len(history)
    if snapshot_count < MIN_SNAPSHOTS:
        available = (
            f"Only {snapshot_count} price snapshot is available"
            if snapshot_count == 1
            else f"Only {snapshot_count} price snapshots are available"
        )
        return TrustScore(
            score=None,
            label="insufficient_data",
            signals=None,
            reasons=[f"{available}; at least {MIN_SNAPSHOTS} are needed for a trustworthy score."],
        )

    signals = compute_signals(history)
    deductions = 0
    reasons: list[str] = []

    if signals.spike_before_discount:
        deductions += SPIKE_PENALTY
        reasons.append(
            "The price rose sharply shortly before the current sale, which can make "
            "the advertised discount misleading."
        )

    if signals.claimed_discount_pct is not None and signals.real_discount_vs_median_pct is not None:
        discount_gap_pct = signals.claimed_discount_pct - signals.real_discount_vs_median_pct
        if discount_gap_pct >= LARGE_DISCOUNT_GAP_THRESHOLD_PCT:
            gap_penalty = LARGE_DISCOUNT_GAP_PENALTY
        elif discount_gap_pct >= MODERATE_DISCOUNT_GAP_THRESHOLD_PCT:
            gap_penalty = MODERATE_DISCOUNT_GAP_PENALTY
        else:
            gap_penalty = 0

        if gap_penalty:
            deductions += gap_penalty
            reasons.append(
                f"The advertised discount is {discount_gap_pct:.1f} percentage points "
                "larger than the saving against the product's earlier typical price."
            )

    if signals.pct_above_lowest >= PRICE_ABOVE_LOWEST_THRESHOLD_PCT:
        deductions += PRICE_ABOVE_LOWEST_PENALTY
        reasons.append(
            f"Today's price is {signals.pct_above_lowest:.1f}% above the lowest price "
            "seen in this history."
        )

    if signals.volatility_pct >= HIGH_VOLATILITY_THRESHOLD_PCT:
        deductions += HIGH_VOLATILITY_PENALTY
        reasons.append(
            f"The price has changed substantially over time, with "
            f"{signals.volatility_pct:.1f}% volatility."
        )

    if not reasons:
        reasons.append("The recorded prices show no strong signs of an inflated discount.")

    score = max(0, 100 - deductions)
    if score >= 70:
        label: Label = "genuine"
    elif score >= 40:
        label = "uncertain"
    else:
        label = "likely_inflated"

    return TrustScore(score=score, label=label, signals=signals, reasons=reasons)
