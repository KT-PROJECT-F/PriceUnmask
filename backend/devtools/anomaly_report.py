"""Print anomaly-detection findings for every product in the configured database.

From PowerShell, point DATABASE_URL at an exported SQLite database and run:

    $env:DATABASE_URL = 'sqlite:///data/exports/priceunmask-20261019.db'
    python -m backend.devtools.anomaly_report
"""

from collections import Counter
from dataclasses import dataclass

import pandas as pd
from sqlalchemy.exc import OperationalError

from backend.analysis.anomaly_model import (
    MIN_CHANGE_PERCENT,
    ROLLING_WINDOW,
    ZSCORE_THRESHOLD,
    AnomalyResult,
    detect_anomalies,
)
from backend.config import settings
from backend.converters import snapshots_to_dataframe
from backend.db import crud
from backend.db.database import SessionLocal
from backend.db.models import Product
from backend.devtools.export_db import sqlite_url_to_path


@dataclass
class ProductAnalysis:
    product: Product
    history: pd.DataFrame
    result: AnomalyResult


def _display_price(price_minor: int | float, currency: str) -> str:
    return f"{currency} {price_minor / 100:,.2f}"


def _timestamp_key(timestamp: pd.Timestamp) -> str:
    return timestamp.isoformat().replace("+00:00", "Z")


def _print_worked_row(analysis: ProductAnalysis, *, prefer_flagged: bool) -> None:
    history = analysis.history
    prices = history["current_price_minor"]
    anomaly_timestamps = set(analysis.result.anomalous_timestamps)
    scored_rows = range(ROLLING_WINDOW, len(history))
    eligible_rows = [
        index
        for index in scored_rows
        if (_timestamp_key(history.iloc[index]["scraped_at"]) in anomaly_timestamps)
        == prefer_flagged
    ]

    if not eligible_rows:
        print("  No scored row matches this example.")
        return

    row_index = eligible_rows[0] if prefer_flagged else eligible_rows[-1]
    window = prices.iloc[row_index - ROLLING_WINDOW : row_index]
    current_price = int(prices.iloc[row_index])
    mean = float(window.mean())
    std = float(window.std(ddof=1))
    z_score = (current_price - mean) / std if std else None
    percent_change = abs(current_price - mean) / abs(mean) * 100 if mean else float("inf")
    is_flagged = _timestamp_key(history.iloc[row_index]["scraped_at"]) in anomaly_timestamps
    flat_baseline = std == 0
    currency = analysis.product.currency

    print(
        f"  Row: {_timestamp_key(history.iloc[row_index]['scraped_at'])}, "
        f"price {_display_price(current_price, currency)}"
    )
    print(
        f"  Previous {ROLLING_WINDOW}: "
        + ", ".join(_display_price(int(price), currency) for price in window)
    )
    print(f"  Mean: {mean:.4f} minor units ({_display_price(mean, currency)})")
    print(f"  Sample std (ddof=1): {std:.4f} minor units")
    if z_score is None:
        print("  z: undefined (flat window has zero standard deviation)")
    else:
        print(f"  z = (price - mean) / std = {z_score:.4f}")
    print(f"  Absolute change from mean: {percent_change:.2f}%")
    if flat_baseline:
        print(
            f"  Flat-window rule: {'met' if percent_change >= MIN_CHANGE_PERCENT else 'not met'}; "
            f"requires at least {MIN_CHANGE_PERCENT:.0f}% change."
        )
    else:
        print(
            f"  Non-flat rule: change >= {MIN_CHANGE_PERCENT:.0f}% is "
            f"{percent_change >= MIN_CHANGE_PERCENT}; |z| >= {ZSCORE_THRESHOLD:g} is "
            f"{z_score is not None and abs(z_score) >= ZSCORE_THRESHOLD}."
        )
    print(f"  Model result for this row: {'FLAGGED' if is_flagged else 'not flagged'}")


def _print_example(
    analysis: ProductAnalysis,
    label: str,
    *,
    prefer_flagged: bool,
) -> None:
    product = analysis.product
    prices = analysis.history["current_price_minor"]
    print(f"\n{label}: {product.name} ({product.source}, {product.currency})")
    print(
        f"  Snapshots: {len(prices)}; "
        f"flagged snapshots: {len(analysis.result.anomalous_timestamps)}"
    )
    print(
        "  Complete price history: "
        + ", ".join(_display_price(int(price), product.currency) for price in prices)
    )
    _print_worked_row(analysis, prefer_flagged=prefer_flagged)


def report() -> None:
    """Analyze all products using the same CRUD and conversion path as the API."""
    database_path = sqlite_url_to_path(settings.database_url)
    if not database_path.is_file():
        raise FileNotFoundError(f"Database does not exist: {database_path}")

    with SessionLocal() as session:
        product_count = crud.count_products(session)
        products = crud.list_products(session)
        inactive_count = product_count - len(products)
        if not products:
            raise RuntimeError(f"No products found in database: {database_path.name}")

        analyses = []
        for product in products:
            history = snapshots_to_dataframe(crud.get_history(session, product.id))
            analyses.append(
                ProductAnalysis(
                    product=product,
                    history=history,
                    result=detect_anomalies(history),
                )
            )

    snapshot_counts = [len(analysis.history) for analysis in analyses]
    products_with_price_changes = sum(
        analysis.history["current_price_minor"].nunique() > 1 for analysis in analyses
    )
    too_little = sum(count <= ROLLING_WINDOW for count in snapshot_counts)
    flagged = [analysis for analysis in analyses if analysis.result.anomalous_timestamps]
    latest_flagged = sum(analysis.result.latest_is_anomalous for analysis in analyses)
    total_flags = sum(len(analysis.result.anomalous_timestamps) for analysis in analyses)
    scoreable_rows = sum(max(count - ROLLING_WINDOW, 0) for count in snapshot_counts)
    timestamps = pd.concat([analysis.history["scraped_at"] for analysis in analyses])

    print(f"Database file: {database_path.name}")
    print(f"Products analyzed: {len(analyses)} of {product_count}")
    if inactive_count:
        print(f"Inactive products skipped: {inactive_count}")
    print(
        "Snapshots per product: "
        f"min={min(snapshot_counts)}, median={pd.Series(snapshot_counts).median():g}, "
        f"max={max(snapshot_counts)}"
    )
    print(f"Products with too little history (<= {ROLLING_WINDOW} snapshots): {too_little}")
    print(f"Products with any observed price change: {products_with_price_changes}")
    print(f"Products flagged at least once: {len(flagged)}")
    print(f"Products whose latest price is flagged: {latest_flagged}")
    print(f"Total flagged snapshots: {total_flags}")
    print(f"Scoreable rows after the first {ROLLING_WINDOW} snapshots: {scoreable_rows}")
    print(
        "Observed snapshot span (UTC): "
        f"{timestamps.min().isoformat()} to {timestamps.max().isoformat()}"
    )
    print("Snapshot-count distribution: " + str(dict(sorted(Counter(snapshot_counts).items()))))

    if flagged:
        _print_example(
            flagged[0],
            "Flagged example",
            prefer_flagged=True,
        )
    else:
        print("\nFlagged example: none; no product had a flagged snapshot.")

    never_flagged = next(
        (analysis for analysis in analyses if not analysis.result.anomalous_timestamps), None
    )
    if never_flagged is not None:
        if flagged:
            _print_example(
                never_flagged,
                "Never-flagged example",
                prefer_flagged=False,
            )
        else:
            print(
                "\nNo flagged product exists in this export; showing two real "
                "never-flagged products instead."
            )
            examples = [
                analysis for analysis in analyses if not analysis.result.anomalous_timestamps
            ][:2]
            for index, analysis in enumerate(examples, start=1):
                _print_example(
                    analysis,
                    f"Observed never-flagged example {index}",
                    prefer_flagged=False,
                )
    else:
        print("\nNever-flagged example: none; every product had at least one flagged snapshot.")


def main() -> None:
    """Run the read-only report and surface database access failures."""
    try:
        report()
    except OperationalError as exc:
        raise SystemExit(f"Cannot read the configured database: {exc}") from exc
    except (FileNotFoundError, RuntimeError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
