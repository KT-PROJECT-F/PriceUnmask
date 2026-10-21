"""Convert anomaly detection results into shopper-friendly summaries."""

from dataclasses import dataclass
from typing import Literal

import pandas as pd

from backend.analysis.anomaly_model import ROLLING_WINDOW, detect_anomalies

MIN_SNAPSHOTS = ROLLING_WINDOW + 1

AnomalyStatus = Literal["insufficient_history", "normal", "unusual"]

INSUFFICIENT_HISTORY_MESSAGE = "Not enough price history to detect unusual price changes."
NORMAL_MESSAGE = "Today's price looks normal based on the available history."

UNUSUAL_MESSAGE = (
    "An unusual price change was detected. "
    "Please review the price history before making a purchase."
)


@dataclass
class AnomalySummary:
    status: AnomalyStatus
    result: bool | None
    message: str


def summarize_anomalies(history: pd.DataFrame) -> AnomalySummary:
    """Return a shopper-friendly status without exposing the detector's note."""
    if len(history) < MIN_SNAPSHOTS:
        return AnomalySummary(
            status="insufficient_history",
            result=None,
            message=INSUFFICIENT_HISTORY_MESSAGE,
        )

    result = detect_anomalies(history)

    if result.latest_is_anomalous:
        return AnomalySummary(
            status="unusual",
            result=True,
            message=UNUSUAL_MESSAGE,
        )

    return AnomalySummary(
        status="normal",
        result=False,
        message=NORMAL_MESSAGE,
    )
