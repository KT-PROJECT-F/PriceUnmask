import pandas as pd
import pytest

from backend.analysis.price_drop import detect_price_drop
from backend.analysis.price_trend import calculate_price_trend


def make_history(prices):
    return pd.DataFrame(
        {
            "scraped_at": pd.date_range(
                "2026-01-01",
                periods=len(prices),
                freq="D",
                tz="UTC",
            ),
            "current_price_minor": prices,
        }
    )


def test_price_drop_detected():
    result = detect_price_drop(make_history([100000, 80000]))

    assert result.status == "price_dropped"
    assert result.drop_amount_minor == 20000
    assert result.drop_percent == 20.0


def test_no_price_drop_when_price_increases():
    result = detect_price_drop(make_history([80000, 100000]))

    assert result.status == "no_drop"
    assert result.drop_amount_minor == 0
    assert result.drop_percent == 0.0


def test_no_price_drop_when_price_is_same():
    result = detect_price_drop(make_history([100000, 100000]))

    assert result.status == "no_drop"


def test_price_drop_insufficient_history():
    result = detect_price_drop(make_history([100000]))

    assert result.status == "insufficient_history"
    assert result.drop_percent is None


def test_price_drop_uses_latest_two_records():
    result = detect_price_drop(make_history([100000, 90000, 70000]))

    assert result.previous_price_minor == 90000
    assert result.current_price_minor == 70000
    assert result.drop_percent == 22.22


def test_price_drop_ignores_zero_price():
    result = detect_price_drop(make_history([100000, 0, 90000]))

    assert result.status == "price_dropped"
    assert result.previous_price_minor == 100000
    assert result.current_price_minor == 90000
    assert result.drop_percent == 10.0


def test_price_drop_ignores_missing_price():
    result = detect_price_drop(make_history([100000, None, 90000]))

    assert result.status == "price_dropped"
    assert result.previous_price_minor == 100000
    assert result.current_price_minor == 90000
    assert result.drop_percent == 10.0


def test_increasing_price_trend():
    result = calculate_price_trend(make_history([80000, 90000, 100000]))

    assert result.direction == "increasing"
    assert result.change_percent == 25.0


def test_decreasing_price_trend():
    result = calculate_price_trend(make_history([100000, 90000, 80000]))

    assert result.direction == "decreasing"
    assert result.change_percent == -20.0


def test_stable_price_trend():
    result = calculate_price_trend(make_history([100000, 100000]))

    assert result.direction == "stable"
    assert result.change_percent == 0.0


def test_trend_insufficient_history():
    result = calculate_price_trend(make_history([100000]))

    assert result.direction == "insufficient_history"
    assert result.snapshot_count == 1


def test_trend_uses_earliest_and_latest_prices():
    result = calculate_price_trend(make_history([100000, 120000, 80000]))

    assert result.first_price_minor == 100000
    assert result.latest_price_minor == 80000
    assert result.change_percent == -20.0


def test_price_trend_ignores_zero_price():
    result = calculate_price_trend(make_history([100000, 0, 90000]))

    assert result.direction == "decreasing"
    assert result.first_price_minor == 100000
    assert result.latest_price_minor == 90000
    assert result.change_percent == -10.0
    assert result.snapshot_count == 2


def test_price_trend_ignores_missing_price():
    result = calculate_price_trend(make_history([100000, None, 90000]))

    assert result.direction == "decreasing"
    assert result.first_price_minor == 100000
    assert result.latest_price_minor == 90000
    assert result.change_percent == -10.0
    assert result.snapshot_count == 2


def test_missing_columns_raise_error():
    history = pd.DataFrame({"current_price_minor": [100000, 80000]})

    with pytest.raises(ValueError):
        detect_price_drop(history)

    with pytest.raises(ValueError):
        calculate_price_trend(history)


def test_zero_price_is_filtered():
    history = make_history([0, 80000])

    drop_result = detect_price_drop(history)
    trend_result = calculate_price_trend(history)

    assert drop_result.status == "insufficient_history"
    assert trend_result.direction == "insufficient_history"
    assert trend_result.snapshot_count == 1
