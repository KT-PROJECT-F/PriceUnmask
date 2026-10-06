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
    assert signals.volatility_pct == pytest.approx(11.87, rel=1e-2)


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
