import numpy as np
import pandas as pd


def get_valid_price_history(history: pd.DataFrame) -> pd.DataFrame:
    """
    Return price history containing only valid price records.

    Invalid dates, negative prices, and non-finite prices are skipped.
    Zero prices are retained as valid baseline values.
    """

    if history.empty:
        return history.copy()

    required_columns = {"scraped_at", "current_price_minor"}

    if not required_columns.issubset(history.columns):
        return history.iloc[0:0].copy()

    valid_history = history.copy()

    valid_history["current_price_minor"] = pd.to_numeric(
        valid_history["current_price_minor"],
        errors="coerce",
    )

    valid_history["scraped_at"] = pd.to_datetime(
        valid_history["scraped_at"],
        errors="coerce",
        utc=True,
    )

    valid_history = valid_history.dropna(subset=["scraped_at", "current_price_minor"])

    valid_history = valid_history[np.isfinite(valid_history["current_price_minor"])]

    valid_history = valid_history[valid_history["current_price_minor"] >= 0]

    valid_history = valid_history.sort_values(
        "scraped_at",
        kind="stable",
        ignore_index=True,
    )

    return valid_history
