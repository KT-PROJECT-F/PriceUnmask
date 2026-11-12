"""Exploratory per-product comparison of rolling z-score and IsolationForest."""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from backend.analysis.anomaly_model import detect_anomalies
from backend.devtools.anomaly_fixtures import (
    ANOMALY_COMPARISON_FIXTURES,
    SCORE_COMPARISON_BASELINE,
    SCORE_COMPARISON_PRICES,
)

MIN_HISTORY_LENGTH = 6
RANDOM_STATES = [0, 21, 42, 99]

ISOLATION_FOREST_SETTINGS = {
    "n_estimators": 100,
    "contamination": 0.2,
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


def predict_latest_with_isolation_forest(
    prices: list[int],
    random_state: int,
) -> bool:
    """Fit on one product's baseline and score only its latest price."""
    baseline = np.asarray(prices[:-1], dtype=float).reshape(-1, 1)
    latest_price = np.asarray([[prices[-1]]], dtype=float)

    model = IsolationForest(
        **ISOLATION_FOREST_SETTINGS,
        random_state=random_state,
    )
    model.fit(baseline)

    return bool(model.predict(latest_price)[0] == -1)


def compare_extreme_price_scores() -> None:
    """Compare scores for prices inside and outside the baseline range."""
    baseline = np.asarray(SCORE_COMPARISON_BASELINE, dtype=float).reshape(-1, 1)
    test_prices = np.asarray(SCORE_COMPARISON_PRICES, dtype=float).reshape(-1, 1)

    print("\nExtreme-price score comparison")
    print("-" * 65)

    for random_state in RANDOM_STATES:
        model = IsolationForest(
            **ISOLATION_FOREST_SETTINGS,
            random_state=random_state,
        )
        model.fit(baseline)

        scores = model.score_samples(test_prices)
        predictions = model.predict(test_prices)

        print(f"\nrandom_state={random_state}")
        for price, score, prediction in zip(
            SCORE_COMPARISON_PRICES,
            scores,
            predictions,
            strict=True,
        ):
            label = "Anomaly" if prediction == -1 else "Normal"
            print(f"  Price {price}: score={score:.8f}, prediction={label}")


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
    expected_labels = [fixture["expected_anomaly"] for fixture in ANOMALY_COMPARISON_FIXTURES]
    zscore_predictions = []

    print("Per-product synthetic anomaly detector comparison")
    print("=" * 65)

    for fixture in ANOMALY_COMPARISON_FIXTURES:
        prices = fixture["prices"]

        if len(prices) < MIN_HISTORY_LENGTH:
            raise ValueError(f"{fixture['name']} has fewer than {MIN_HISTORY_LENGTH} snapshots.")

        history = make_history(prices)
        result = detect_anomalies(history)
        latest_timestamp = history["scraped_at"].iloc[-1].isoformat().replace("+00:00", "Z")
        zscore_flagged = latest_timestamp in result.anomalous_timestamps
        zscore_predictions.append(zscore_flagged)

        print(f"\n{fixture['name']}")
        print(f"  Baseline prices: {prices[:-1]}")
        print(f"  Latest price: {prices[-1]}")
        print(f"  Expected anomaly: {fixture['expected_anomaly']}")
        print(f"  Rolling z-score flagged: {zscore_flagged}")

    print("\nIsolationForest settings")
    print("-" * 65)
    print(f"  n_estimators: {ISOLATION_FOREST_SETTINGS['n_estimators']}")
    print(f"  contamination: {ISOLATION_FOREST_SETTINGS['contamination']}")
    print(f"  random_state values: {RANDOM_STATES}")
    print("  training: each product's first five prices")
    print("  prediction: that product's latest price only")
    print("  evaluation: four independent, small synthetic fixtures")

    all_predictions = {}

    for random_state in RANDOM_STATES:
        predictions = []

        print(f"\nIsolationForest predictions (random_state={random_state})")
        print("-" * 65)

        for fixture in ANOMALY_COMPARISON_FIXTURES:
            flagged = predict_latest_with_isolation_forest(
                fixture["prices"],
                random_state,
            )
            predictions.append(flagged)
            print(f"  {fixture['name']}: {'Flagged' if flagged else 'Not flagged'}")

        all_predictions[random_state] = predictions

        metrics = calculate_metrics(expected_labels, predictions)
        print("  Metrics:")
        for metric, count in metrics.items():
            print(f"    {metric.replace('_', ' ')}: {count}")

    print("\nRolling z-score metrics")
    print("-" * 65)
    for metric, count in calculate_metrics(
        expected_labels,
        zscore_predictions,
    ).items():
        print(f"  {metric.replace('_', ' ')}: {count}")

    compare_extreme_price_scores()

    print("\nIMPORTANT: Each IsolationForest model was fitted on only five")
    print("baseline prices from one product and scored on that product's")
    print("latest price. These four synthetic fixtures are exploratory only.")
    print("They do not establish real-world accuracy or justify replacing")
    print("the current production detector.")


if __name__ == "__main__":
    main()
