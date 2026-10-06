import pandas as pd
import pytest

from backend.analysis.trust_score import compute_signals


def test_compute_signals_basic_history() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.to_datetime(
                [
                    "2026-10-01 10:00:00+00:00",
                    "2026-10-02 10:00:00+00:00",
                    "2026-10-03 10:00:00+00:00",
                    "2026-10-04 10:00:00+00:00",
                    "2026-10-05 10:00:00+00:00",
                ]
            ),
            "current_price_minor": [1000, 900, 1100, 800, 1000],
            "original_price_minor": [1500, 1500, 1500, 1500, 1500],
        }
    )

    signals = compute_signals(history)

    assert signals.snapshot_count == 5
    assert signals.days_of_history == 4
    assert signals.lowest_price_minor == 800
    assert signals.pct_above_lowest == 25.0

    # Check the exact expected value based on your implementation.
    # mean 960, sample std ≈ 114.02 -> 114.02 / 960 ≈ 11.877%
    assert signals.volatility_pct == pytest.approx(11.877, abs=0.001)
    assert type(signals.pct_above_lowest) is float
    assert type(signals.volatility_pct) is float


def test_compute_signals_constant_price() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.to_datetime(
                [
                    "2026-10-01 10:00:00+00:00",
                    "2026-10-02 10:00:00+00:00",
                    "2026-10-03 10:00:00+00:00",
                ]
            ),
            "current_price_minor": [1000, 1000, 1000],
            "original_price_minor": [1500, 1500, 1500],
        }
    )

    signals = compute_signals(history)

    assert signals.lowest_price_minor == 1000
    assert signals.pct_above_lowest == 0.0
    assert signals.volatility_pct == 0.0


def test_compute_signals_single_row() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.to_datetime(["2026-10-01 10:00:00+00:00"]),
            "current_price_minor": [1000],
            "original_price_minor": [1500],
        }
    )

    signals = compute_signals(history)

    assert signals.snapshot_count == 1
    assert signals.days_of_history == 0
    assert signals.lowest_price_minor == 1000
    assert signals.pct_above_lowest == 0.0
    assert signals.volatility_pct == 0.0


def test_compute_signals_today_is_lowest() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.to_datetime(
                [
                    "2026-10-01 10:00:00+00:00",
                    "2026-10-02 10:00:00+00:00",
                    "2026-10-03 10:00:00+00:00",
                    "2026-10-04 10:00:00+00:00",
                ]
            ),
            "current_price_minor": [1000, 1200, 1100, 800],
            "original_price_minor": [1500, 1500, 1500, 1500],
        }
    )

    signals = compute_signals(history)

    assert signals.lowest_price_minor == 800
    assert signals.pct_above_lowest == 0.0


def test_compute_signals_empty_history() -> None:
    history = pd.DataFrame(
        columns=[
            "scraped_at",
            "current_price_minor",
            "original_price_minor",
        ]
    )

    with pytest.raises(ValueError, match="history must contain at least one row"):
        compute_signals(history)


def test_compute_signals_detects_recent_spike_before_sale() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.date_range("2026-09-30", periods=11, tz="UTC"),
            "current_price_minor": [
                1000,
                1000,
                1000,
                1000,
                3000,
                3000,
                1050,
                1050,
                1050,
                1050,
                1050,
            ],
            "original_price_minor": [None] * 10 + [3500],
        }
    )

    signals = compute_signals(history)

    assert signals.spike_before_discount is True
    assert signals.spike_pct == pytest.approx(200.0)


def test_compute_signals_stable_price_with_small_sale_has_no_spike() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.date_range("2026-10-01", periods=10, tz="UTC"),
            "current_price_minor": [2000] * 9 + [1900],
            "original_price_minor": [None] * 9 + [2100],
        }
    )

    signals = compute_signals(history)

    assert signals.spike_before_discount is False
    assert signals.spike_pct == 0.0


def test_compute_signals_no_strikethrough_price_has_no_claimed_discount() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.date_range("2026-10-01", periods=2, tz="UTC"),
            "current_price_minor": [1000, 900],
            "original_price_minor": [None, None],
        }
    )

    signals = compute_signals(history)

    assert signals.claimed_discount_pct is None


def test_compute_signals_calculates_claimed_discount_from_latest_row() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.date_range("2026-10-01", periods=2, tz="UTC"),
            "current_price_minor": [2000, 1500],
            "original_price_minor": [2500, 3000],
        }
    )

    signals = compute_signals(history)

    assert signals.claimed_discount_pct == 50.0


def test_compute_signals_real_discount_uses_median_of_earlier_prices() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.date_range("2026-10-01", periods=5, tz="UTC"),
            "current_price_minor": [2000, 2100, 1900, 2000, 1000],
            "original_price_minor": [None] * 5,
        }
    )

    signals = compute_signals(history)

    assert signals.real_discount_vs_median_pct == 50.0


def test_compute_signals_spike_is_not_reported_without_enough_history() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.date_range("2026-10-01", periods=3, tz="UTC"),
            "current_price_minor": [1000, 2000, 1000],
            "original_price_minor": [None, None, 1500],
        }
    )

    signals = compute_signals(history)

    assert signals.spike_before_discount is False
    assert signals.spike_pct is None
