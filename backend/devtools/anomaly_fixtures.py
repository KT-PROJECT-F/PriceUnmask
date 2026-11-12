"""Shared synthetic price histories for anomaly tests and comparisons."""

SIGNIFICANT_DROP = [1000, 1010, 990, 1000, 1000, 800]
SMALL_INCREASE = [1000, 1010, 990, 1000, 1000, 1030]
SIGNIFICANT_HIKE = [1000, 1010, 990, 1000, 1000, 1200]
VOLATILE_BASELINE = [700, 1300, 800, 1200, 1000, 700]

SCORE_COMPARISON_BASELINE = [1000, 1010, 990, 1000, 1000]
SCORE_COMPARISON_PRICES = [800, 990, 1030, 1200, 5000]

ANOMALY_REPORT_HISTORIES = {
    "Significant drop": SIGNIFICANT_DROP,
    "Significant hike": SIGNIFICANT_HIKE,
    "Volatile baseline": VOLATILE_BASELINE,
}

ANOMALY_COMPARISON_FIXTURES = [
    {
        "name": "Significant drop",
        "prices": SIGNIFICANT_DROP,
        "expected_anomaly": True,
    },
    {
        "name": "Small increase",
        "prices": SMALL_INCREASE,
        "expected_anomaly": False,
    },
    {
        "name": "Significant hike",
        "prices": SIGNIFICANT_HIKE,
        "expected_anomaly": True,
    },
    {
        "name": "Volatile baseline",
        "prices": VOLATILE_BASELINE,
        "expected_anomaly": False,
    },
]
