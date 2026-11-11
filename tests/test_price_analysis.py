import pandas as pd
import pytest

from backend.analysis.price_drop import detect_price_drop
from backend.analysis.price_history_utils import get_valid_price_history
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


# Price drop tests


def test_price_drop_detected():
    result = detect_price_drop(make_history([100000, 80000]))

    assert result.status == "price_dropped"
    assert result.previous_price_minor == 100000
    assert result.current_price_minor == 80000
    assert result.drop_amount_minor == 20000
    assert result.drop_percent == 20.0


def test_no_price_drop_when_price_increases():
    result = detect_price_drop(make_history([80000, 100000]))

    assert result.status == "no_drop"
    assert result.previous_price_minor == 80000
    assert result.current_price_minor == 100000
    assert result.drop_amount_minor == 0
    assert result.drop_percent == 0.0


def test_no_price_drop_when_price_is_same():
    result = detect_price_drop(make_history([100000, 100000]))

    assert result.status == "no_drop"
    assert result.drop_amount_minor == 0
    assert result.drop_percent == 0.0


def test_price_drop_insufficient_history():
    result = detect_price_drop(make_history([100000]))

    assert result.status == "insufficient_history"
    assert result.previous_price_minor is None
    assert result.current_price_minor is None
    assert result.drop_amount_minor is None
    assert result.drop_percent is None


def test_price_drop_uses_start_of_latest_falling_stretch():
    result = detect_price_drop(make_history([100000, 90000, 70000]))

    assert result.previous_price_minor == 100000
    assert result.current_price_minor == 70000
    assert result.drop_amount_minor == 30000
    assert result.drop_percent == 30.0
    assert result.status == "price_dropped"


def test_price_drop_ignores_zero_price():
    result = detect_price_drop(make_history([100000, 0, 90000]))

    assert result.status == "price_dropped"
    assert result.previous_price_minor == 100000
    assert result.current_price_minor == 90000
    assert result.drop_amount_minor == 10000
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


def test_price_drop_ignores_fractional_price():
    result = detect_price_drop(make_history([100000, 999.7, 90000]))

    assert result.status == "price_dropped"
    assert result.previous_price_minor == 100000
    assert result.current_price_minor == 90000
    assert result.drop_percent == 10.0


def test_price_drop_with_only_one_valid_price():
    result = detect_price_drop(make_history([0, 80000]))

    assert result.status == "insufficient_history"
    assert result.previous_price_minor is None
    assert result.current_price_minor is None


def test_price_drop_below_one_percent_is_no_drop():
    result = detect_price_drop(make_history([100000, 99999]))

    assert result.status == "no_drop"
    assert result.drop_amount_minor == 0
    assert result.drop_percent == 0.0


def test_price_drop_at_exactly_one_percent():
    result = detect_price_drop(make_history([100000, 99000]))

    assert result.status == "price_dropped"
    assert result.drop_amount_minor == 1000
    assert result.drop_percent == 1.0


def test_price_drop_above_one_percent():
    result = detect_price_drop(make_history([100000, 98990]))

    assert result.status == "price_dropped"
    assert result.drop_amount_minor == 1010
    assert result.drop_percent == 1.01


def test_price_drop_alert_stays_during_repeated_same_price():
    result = detect_price_drop(make_history([100000, 80000, 80000]))

    assert result.status == "price_dropped"
    assert result.previous_price_minor == 100000
    assert result.current_price_minor == 80000
    assert result.drop_amount_minor == 20000
    assert result.drop_percent == 20.0


def test_price_drop_alert_stays_during_continued_fall():
    result = detect_price_drop(make_history([100000, 80000, 80000, 79500]))

    assert result.status == "price_dropped"
    assert result.previous_price_minor == 100000
    assert result.current_price_minor == 79500
    assert result.drop_amount_minor == 20500
    assert result.drop_percent == 20.5


def test_price_drop_uses_start_of_latest_falling_stretch_after_rise():
    result = detect_price_drop(make_history([100000, 80000, 85000, 84000]))

    assert result.status == "price_dropped"
    assert result.previous_price_minor == 85000
    assert result.current_price_minor == 84000
    assert result.drop_amount_minor == 1000
    assert result.drop_percent == 1.18


def test_price_drop_no_falling_stretch_when_latest_price_rises():
    result = detect_price_drop(make_history([120000, 90000, 99000]))

    assert result.status == "no_drop"
    assert result.previous_price_minor == 90000
    assert result.current_price_minor == 99000


def test_price_drop_no_drop_when_all_prices_are_equal():
    result = detect_price_drop(make_history([100000, 100000, 100000]))

    assert result.status == "no_drop"
    assert result.previous_price_minor == 100000
    assert result.current_price_minor == 100000


def test_price_drop_at_0_99_percent_is_no_drop():
    result = detect_price_drop(make_history([100000, 99010]))

    assert result.status == "no_drop"
    assert result.previous_price_minor == 100000
    assert result.drop_percent == 0.0


def test_price_drop_at_rounded_one_percent_threshold():
    result = detect_price_drop(make_history([100000, 99005]))

    assert result.status == "price_dropped"
    assert result.previous_price_minor == 100000
    assert result.current_price_minor == 99005
    assert result.drop_amount_minor == 995
    assert result.drop_percent == 1.0


def test_price_drop_after_invalid_zero_price_is_detected():
    result = detect_price_drop(make_history([100000, 0, 80000]))

    assert result.status == "price_dropped"
    assert result.previous_price_minor == 100000
    assert result.current_price_minor == 80000
    assert result.drop_amount_minor == 20000
    assert result.drop_percent == 20.0


# Price trend tests


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


def test_price_trend_ignores_fractional_price():
    result = calculate_price_trend(make_history([100000, 999.7, 90000]))

    assert result.direction == "decreasing"
    assert result.first_price_minor == 100000
    assert result.latest_price_minor == 90000
    assert result.snapshot_count == 2


def test_price_trend_with_only_one_valid_price():
    result = calculate_price_trend(make_history([0, 80000]))

    assert result.direction == "insufficient_history"
    assert result.first_price_minor is None
    assert result.latest_price_minor is None
    assert result.change_percent is None
    assert result.snapshot_count == 1


# Shared 1% threshold boundary tests


def test_stable_price_trend_at_0_99_percent_decrease():
    result = calculate_price_trend(make_history([100000, 99010]))

    assert result.direction == "stable"
    assert result.change_percent == -0.99


def test_decreasing_price_trend_at_rounded_one_percent_threshold():
    result = calculate_price_trend(make_history([100000, 99005]))

    assert result.direction == "decreasing"
    assert result.change_percent == -1.0


def test_decreasing_price_trend_at_exactly_one_percent():
    result = calculate_price_trend(make_history([100000, 99000]))

    assert result.direction == "decreasing"
    assert result.change_percent == -1.0


def test_decreasing_price_trend_at_1_01_percent():
    result = calculate_price_trend(make_history([100000, 98990]))

    assert result.direction == "decreasing"
    assert result.change_percent == -1.01


def test_stable_price_trend_below_one_percent_increase():
    result = calculate_price_trend(make_history([100000, 100990]))

    assert result.direction == "stable"
    assert result.change_percent == 0.99


def test_increasing_price_trend_at_exactly_one_percent():
    result = calculate_price_trend(make_history([100000, 101000]))

    assert result.direction == "increasing"
    assert result.change_percent == 1.0


def test_increasing_price_trend_above_one_percent():
    result = calculate_price_trend(make_history([100000, 101010]))

    assert result.direction == "increasing"
    assert result.change_percent == 1.01


# Trend and price-drop comparison tests


def test_small_decrease_is_stable_and_not_a_price_drop():
    history = make_history([100000, 99999])

    trend = calculate_price_trend(history)
    drop = detect_price_drop(history)

    assert trend.direction == "stable"
    assert drop.status == "no_drop"


def test_exactly_one_percent_decrease_is_a_price_drop():
    history = make_history([100000, 99000])

    trend = calculate_price_trend(history)
    drop = detect_price_drop(history)

    assert trend.direction == "decreasing"
    assert drop.status == "price_dropped"
    assert drop.drop_percent == 1.0


def test_trend_and_drop_can_have_different_directions_when_latest_price_rises():
    history = make_history([120000, 90000, 99000])

    trend = calculate_price_trend(history)
    drop = detect_price_drop(history)

    assert trend.direction == "decreasing"
    assert trend.change_percent == -17.5

    assert drop.status == "no_drop"
    assert drop.previous_price_minor == 90000
    assert drop.current_price_minor == 99000
    assert drop.drop_amount_minor == 0
    assert drop.drop_percent == 0.0


def test_price_drop_detected_even_when_overall_trend_is_increasing():
    history = make_history([100000, 120000, 110000])

    trend = calculate_price_trend(history)
    drop = detect_price_drop(history)

    assert trend.direction == "increasing"
    assert trend.change_percent == 10.0

    assert drop.status == "price_dropped"
    assert drop.previous_price_minor == 120000
    assert drop.previous_price_minor != trend.first_price_minor
    assert drop.current_price_minor == 110000
    assert drop.drop_amount_minor == 10000
    assert drop.drop_percent == 8.33


def test_zero_price_is_filtered_consistently():
    history = make_history([100000, 0, 90000])

    trend = calculate_price_trend(history)
    drop = detect_price_drop(history)

    assert trend.direction == "decreasing"
    assert trend.snapshot_count == 2

    assert drop.status == "price_dropped"
    assert drop.previous_price_minor == 100000
    assert drop.current_price_minor == 90000


# Validation and history helper tests


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

    assert result.previous_price_minor == 100000
    assert result.current_price_minor == 70000
    assert result.drop_amount_minor == 30000
    assert result.drop_percent == 30.0
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


# Invalid input tests


def test_price_history_skips_invalid_dates():
    history = pd.DataFrame(
        {
            "scraped_at": [
                "2026-01-01",
                "not a date",
                "2026-01-03",
            ],
            "current_price_minor": [100000, 50000, 90000],
        }
    )

    result = get_valid_price_history(history)

    assert result["current_price_minor"].tolist() == [
        100000,
        90000,
    ]


def test_price_history_skips_infinite_prices():
    history = make_history([100000, float("inf"), float("-inf"), 90000])

    result = get_valid_price_history(history)

    assert result["current_price_minor"].tolist() == [
        100000,
        90000,
    ]


def test_price_history_skips_non_numeric_prices():
    history = make_history([100000, "invalid", 90000])

    result = get_valid_price_history(history)

    assert result["current_price_minor"].tolist() == [
        100000,
        90000,
    ]


def test_price_history_skips_zero_and_negative_prices():
    history = make_history([100000, 0, -500, 90000])

    result = get_valid_price_history(history)

    assert result["current_price_minor"].tolist() == [
        100000,
        90000,
    ]


def test_price_history_skips_fractional_prices():
    history = make_history([100000, 999.7, 90000])

    result = get_valid_price_history(history)

    assert result["current_price_minor"].tolist() == [
        100000,
        90000,
    ]


def test_price_history_keeps_whole_number_float_prices():
    history = make_history([100000, 999.0, 90000])

    result = get_valid_price_history(history)

    assert result["current_price_minor"].tolist() == [
        100000,
        999.0,
        90000,
    ]
