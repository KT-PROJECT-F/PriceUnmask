from backend.devtools.anomaly_comparison import calculate_metrics


def test_calculate_metrics_counts_all_outcomes():
    expected = [True, True, False, False]
    predicted = [True, False, True, False]

    assert calculate_metrics(expected, predicted) == {
        "true_positives": 1,
        "misses": 1,
        "false_alarms": 1,
        "true_negatives": 1,
    }
