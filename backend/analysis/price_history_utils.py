import pandas as pd


def get_valid_price_history(history: pd.DataFrame) -> pd.DataFrame:
    """
    Return price history containing only valid price records.
    """

    if history.empty:
        return history.copy()

    valid_history = history.copy()

    valid_history["current_price_minor"] = pd.to_numeric(
        valid_history["current_price_minor"],
        errors="coerce",
    )

    valid_history = valid_history.dropna(
        subset=["scraped_at", "current_price_minor"]
    )

    valid_history = valid_history[
        valid_history["current_price_minor"] > 0
    ]

    valid_history = valid_history.sort_values("scraped_at")

    return valid_history
