"""Exploratory comparison of z-score and IsolationForest anomaly detection.

Uses the four labelled synthetic fixtures documented for issue #242.
IsolationForest is fitted and scored on the same four cases, so its results
are exploratory only and must not be treated as independent validation.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from backend.analysis.anomaly_model import detect_anomalies

FIXTURES = [
    {
        "name": "Significant drop",
        "prices": [1000, 1010, 990, 1000, 1000, 800],
        "expected_anomaly": True,
    },
    {
        "name": "Small increase",
        "prices": [1000, 1010, 990, 1000, 1000, 1030],
        "expected_anomaly": False,
    },
    {
        "name": "Significant hike",
        "prices": [1000, 1010, 990, 1000, 1000, 1200],
        "expected_anomaly": True,
    },
    {
        "name": "Volatile baseline",
        "prices": [700, 1300, 800, 1200, 1000, 700],
        "expected_anomaly": False,
    },
]

MIN_HISTORY_LENGTH = 6

ISOLATION_FOREST_SETTINGS = {
    "n_estimators": 100,
    "contamination": 0.25,
    "random_state": 42,
}


def make_history(prices: list[int]) -> pd.DataFrame:
    """Build a UTC-dated synthetic price history."""
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


def extract_features(prices: list[int]) -> list[float]:
    """Extract features from the first five prices and the latest price."""
    baseline = np.asarray(prices[:-1], dtype=float)
    latest_price = float(prices[-1])

    baseline_mean = float(np.mean(baseline))
    baseline_std = float(np.std(baseline, ddof=1))

    if baseline_mean == 0:
        raise ValueError("Baseline mean must not be zero.")

    percent_change = ((latest_price - baseline_mean) / abs(baseline_mean)) * 100

    absolute_z_score = (
        abs((latest_price - baseline_mean) / baseline_std) if baseline_std > 0 else 0.0
    )

    baseline_volatility = (baseline_std / abs(baseline_mean)) * 100

    return [
        percent_change,
        absolute_z_score,
        baseline_volatility,
    ]


def calculate_metrics(
    expected: list[bool],
    predicted: list[bool],
) -> dict[str, int]:
    """Calculate true positives, misses, false alarms, and true negatives."""
    true_positives = sum(
        actual and prediction for actual, prediction in zip(expected, predicted, strict=True)
    )

    misses = sum(
        actual and not prediction for actual, prediction in zip(expected, predicted, strict=True)
    )

    false_alarms = sum(
        not actual and prediction for actual, prediction in zip(expected, predicted, strict=True)
    )

    true_negatives = sum(
        not actual and not prediction
        for actual, prediction in zip(expected, predicted, strict=True)
    )

    return {
        "true_positives": true_positives,
        "misses": misses,
        "false_alarms": false_alarms,
        "true_negatives": true_negatives,
    }


def main() -> None:
    expected_labels = [fixture["expected_anomaly"] for fixture in FIXTURES]

    zscore_predictions = []
    feature_rows = []

    print("Synthetic anomaly detector comparison")
    print("=" * 55)

    for fixture in FIXTURES:
        prices = fixture["prices"]

        if len(prices) < MIN_HISTORY_LENGTH:
            raise ValueError(f"{fixture['name']} has fewer than {MIN_HISTORY_LENGTH} snapshots.")

        history = make_history(prices)
        result = detect_anomalies(history)

        # Convert the latest timestamp into the same UTC ISO format
        # returned by detect_anomalies().
        latest_timestamp = history["scraped_at"].iloc[-1].isoformat().replace("+00:00", "Z")

        zscore_flagged = latest_timestamp in result.anomalous_timestamps

        zscore_predictions.append(zscore_flagged)
        feature_rows.append(extract_features(prices))

        print(f"\n{fixture['name']}")
        print(f"  Expected anomaly: {fixture['expected_anomaly']}")
        print(f"  Z-score flagged:  {zscore_flagged}")

    feature_names = [
        "percentage_change",
        "absolute_z_score",
        "baseline_volatility_percent",
    ]

    features = pd.DataFrame(
        feature_rows,
        columns=feature_names,
    )

    isolation_forest = IsolationForest(
        **ISOLATION_FOREST_SETTINGS,
    )

    # IsolationForest returns -1 for an outlier and +1 for an inlier.
    # This is an in-sample exploratory run on only four observations.
    isolation_predictions = isolation_forest.fit_predict(features)

    isolation_flags = [prediction == -1 for prediction in isolation_predictions]

    print("\nIsolationForest settings")
    print("-" * 55)

    for setting, value in ISOLATION_FOREST_SETTINGS.items():
        print(f"  {setting}: {value}")

    print(f"  minimum history length: {MIN_HISTORY_LENGTH} snapshots")
    print(f"  features: {', '.join(feature_names)}")
    print(f"  observations used: {len(FIXTURES)}")
    print("  evaluation: in-sample; exploratory only")

    print("\nFeature values and predictions")
    print("-" * 55)

    for index, fixture in enumerate(FIXTURES):
        print(f"\n{fixture['name']}")

        for feature_name in feature_names:
            print(f"  {feature_name}: {features.iloc[index][feature_name]:.3f}")

        print(f"  IsolationForest flagged: {isolation_flags[index]}")

    print("\nComparison metrics")
    print("-" * 55)

    for detector_name, predictions in [
        ("Rolling z-score", zscore_predictions),
        ("IsolationForest", isolation_flags),
    ]:
        metrics = calculate_metrics(
            expected_labels,
            predictions,
        )

        print(f"\n{detector_name}")

        for metric, count in metrics.items():
            print(f"  {metric.replace('_', ' ')}: {count}")

    print("\nIMPORTANT: IsolationForest was fitted and evaluated on the")
    print("same four synthetic cases. These results are not independent")
    print("validation and do not justify replacing the current detector.")


if __name__ == "__main__":
    main()
