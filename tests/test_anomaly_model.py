import pandas as pd

from backend.analysis.anomaly_model import AnomalyResult, detect_anomalies


def make_history(prices: list[int]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "scraped_at": pd.date_range(
                "2026-10-01",
                periods=len(prices),
                freq="D",
                tz="UTC",
            ),
            "current_price_minor": prices,
        }
    )


def test_detect_anomalies_returns_result_for_empty_history() -> None:
    result = detect_anomalies(pd.DataFrame())

    assert result == AnomalyResult(
        method="zscore",
        anomalous_timestamps=[],
        latest_is_anomalous=False,
        note="No snapshots are available.",
    )


def test_detect_anomalies_skips_history_shorter_than_six_snapshots() -> None:
    result = detect_anomalies(make_history([1000, 1010, 990, 1000]))

    assert result.method == "zscore"
    assert result.anomalous_timestamps == []
    assert not result.latest_is_anomalous
    assert "at least 6" in result.note


def test_detect_anomalies_does_not_flag_a_flat_price() -> None:
    result = detect_anomalies(make_history([1000, 1000, 1000, 1000, 1000, 1000]))

    assert result.anomalous_timestamps == []
    assert not result.latest_is_anomalous
    assert "zero-standard-deviation" in result.note


def test_detect_anomalies_flags_jump_after_flat_prices() -> None:
    result = detect_anomalies(make_history([1000, 1000, 1000, 1000, 1000, 2000]))

    assert result.anomalous_timestamps == ["2026-10-06T00:00:00Z"]
    assert result.latest_is_anomalous


def test_detect_anomalies_flags_an_obvious_high_spike() -> None:
    # The prior five average 1000; sample std is sqrt(50), so 1200 has z ~= 28.28.
    history = make_history([1000, 1010, 990, 1000, 1000, 1200])

    result = detect_anomalies(history)

    assert result.method == "zscore"
    assert result.anomalous_timestamps == ["2026-10-06T00:00:00Z"]
    assert result.latest_is_anomalous


def test_detect_anomalies_does_not_flag_a_slow_steady_rise() -> None:
    result = detect_anomalies(make_history([1000, 1010, 1020, 1030, 1040, 1050, 1060]))

    assert result.anomalous_timestamps == []
    assert not result.latest_is_anomalous


def test_detect_anomalies_flags_a_sudden_big_drop() -> None:
    result = detect_anomalies(make_history([1000, 1010, 990, 1000, 1000, 800]))

    assert result.anomalous_timestamps == ["2026-10-06T00:00:00Z"]
    assert result.latest_is_anomalous


def test_detect_anomalies_reports_latest_status_separately() -> None:
    result = detect_anomalies(make_history([1000, 1010, 990, 1000, 1000, 1200, 1000]))

    assert result.anomalous_timestamps == ["2026-10-06T00:00:00Z"]
    assert not result.latest_is_anomalous


def test_detect_anomalies_sorts_rows_and_normalizes_timestamps_to_utc() -> None:
    history = make_history([1000, 1010, 990, 1000, 1000, 1200]).iloc[::-1]

    result = detect_anomalies(history)

    assert result.anomalous_timestamps == ["2026-10-06T00:00:00Z"]
    assert result.latest_is_anomalous
