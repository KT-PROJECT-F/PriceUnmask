import pandas as pd
import pytest

from backend.analysis.price_drop import detect_price_drop
from backend.analysis.price_trend import calculate_price_trend
from backend.analysis.price_history_utils import get_valid_price_history


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


def test_price_drop_ignores_nan_price():
    result = detect_price_drop(make_history([100000, float("nan"), 90000]))

    assert result.status == "price_dropped"
    assert result.previous_price_minor == 100000
    assert result.current_price_minor == 90000


def test_price_drop_ignores_negative_price():
    result = detect_price_drop(make_history([100000, -500, 90000]))

    assert result.status == "price_dropped"
    assert result.previous_price_minor == 100000
    assert result.current_price_minor == 90000


def test_price_drop_with_zero_price_has_insufficient_history():
    result = detect_price_drop(make_history([0, 80000]))

    assert result.status == "insufficient_history"


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


def test_price_trend_ignores_nan_price():
    result = calculate_price_trend(make_history([100000, float("nan"), 90000]))

    assert result.direction == "decreasing"
    assert result.first_price_minor == 100000
    assert result.latest_price_minor == 90000
    assert result.snapshot_count == 2


def test_price_trend_ignores_negative_price():
    result = calculate_price_trend(make_history([100000, -500, 90000]))

    assert result.direction == "decreasing"
    assert result.first_price_minor == 100000
    assert result.latest_price_minor == 90000
    assert result.snapshot_count == 2


def test_price_trend_with_zero_price_has_insufficient_history():
    result = calculate_price_trend(make_history([0, 80000]))

    assert result.direction == "insufficient_history"
    assert result.snapshot_count == 1


def test_missing_columns_raise_error():
    history = pd.DataFrame({"current_price_minor": [100000, 80000]})

    with pytest.raises(ValueError):
        detect_price_drop(history)

    with pytest.raises(ValueError):
        calculate_price_trend(history)


def test_empty_history_with_required_columns():
    history = pd.DataFrame(columns=["scraped_at", "current_price_minor"])

    drop_result = detect_price_drop(history)
    trend_result = calculate_price_trend(history)

    assert drop_result.status == "insufficient_history"
    assert trend_result.direction == "insufficient_history"
    assert trend_result.snapshot_count == 0


def test_unsorted_history_is_sorted_before_price_drop():
    history = pd.DataFrame(
        {
            "scraped_at": pd.to_datetime(
                [
                    "2026-01-03",
                    "2026-01-01",
                    "2026-01-02",
                ],
                utc=True,
            ),
            "current_price_minor": [70000, 100000, 90000],
        }
    )

    result = detect_price_drop(history)

    assert result.previous_price_minor == 90000
    assert result.current_price_minor == 70000
    assert result.status == "price_dropped"


def test_unsorted_history_is_sorted_before_price_trend():
    history = pd.DataFrame(
        {
            "scraped_at": pd.to_datetime(
                [
                    "2026-01-03",
                    "2026-01-01",
                    "2026-01-02",
                ],
                utc=True,
            ),
            "current_price_minor": [70000, 100000, 90000],
        }
    )

    result = calculate_price_trend(history)

    assert result.first_price_minor == 100000
    assert result.latest_price_minor == 70000
    assert result.direction == "decreasing"


def test_same_timestamp_preserves_original_order():
    history = pd.DataFrame(
        {
            "scraped_at": [
                "2026-01-01T10:00:00Z",
                "2026-01-01T10:00:00Z",
                "2026-01-02T10:00:00Z",
            ],
            "current_price_minor": [100000, 90000, 80000],
        }
    )

    result = get_valid_price_history(history)

    assert result["current_price_minor"].tolist() == [
        100000,
        90000,
        80000,
    ]


def test_naive_timestamps_are_converted_to_utc():
    history = pd.DataFrame(
        {
            "scraped_at": [
                "2026-01-02 10:00:00",
                "2026-01-01 10:00:00",
            ],
            "current_price_minor": [80000, 100000],
        }
    )

    result = get_valid_price_history(history)

    assert str(result["scraped_at"].dt.tz) == "UTC"
    assert result["current_price_minor"].tolist() == [100000, 80000]


def test_timezone_aware_timestamps_are_converted_to_utc():
    history = pd.DataFrame(
        {
            "scraped_at": [
                "2026-01-02T10:00:00+05:30",
                "2026-01-01T10:00:00+05:30",
            ],
            "current_price_minor": [80000, 100000],
        }
    )

    result = get_valid_price_history(history)

    assert str(result["scraped_at"].dt.tz) == "UTC"
    assert result["current_price_minor"].tolist() == [100000, 80000]
