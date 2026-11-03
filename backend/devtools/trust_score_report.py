"""Print Trust Score findings for every product in the configured database.

From the repository root, set DATABASE_URL to an exported SQLite database and run:

    $env:DATABASE_URL = 'sqlite:///data/exports/priceunmask-20261019.db'
    python -m backend.devtools.trust_score_report
"""

from collections import Counter
from dataclasses import dataclass

import pandas as pd
from sqlalchemy.exc import OperationalError

from backend.analysis.trust_score import TrustScore, compute_trust_score
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
    result: TrustScore


def summarize(analyses: list[ProductAnalysis]) -> dict[str, object]:
    """Calculate report metrics from already-computed product analyses."""
    labels = Counter(analysis.result.label for analysis in analyses)
    scores = Counter(
        analysis.result.score for analysis in analyses if analysis.result.score is not None
    )
    snapshot_counts = [len(analysis.history) for analysis in analyses]
    products_with_original_price = sum(
        not analysis.history.empty
        and "original_price_minor" in analysis.history.columns
        and analysis.history["original_price_minor"].notna().any()
        for analysis in analyses
    )
    total_snapshots = sum(snapshot_counts)

    return {
        "product_count": len(analyses),
        "total_snapshots": total_snapshots,
        "snapshot_counts": dict(sorted(Counter(snapshot_counts).items())),
        "products_with_original_price": products_with_original_price,
        "labels": dict(sorted(labels.items())),
        "scores": dict(sorted(scores.items())),
    }


def _display_price(price_minor: int, currency: str) -> str:
    return f"{currency} {price_minor / 100:,.2f}"


def _print_example(analysis: ProductAnalysis) -> None:
    product = analysis.product
    result = analysis.result

    print(f"\n{product.name} (product ID {product.id})")
    print(f"  Source and currency: {product.source}, {product.currency}")
    print(f"  Snapshots: {len(analysis.history)}")
    print(f"  Score: {result.score}")
    print(f"  Label: {result.label}")
    print(f"  Reasons: {result.reasons}")

    if result.signals is not None:
        signals = result.signals
        print(f"  Days of history: {signals.days_of_history:.2f}")
        print(f"  Lowest price: {_display_price(signals.lowest_price_minor, product.currency)}")
        print(f"  Price above lowest: {signals.pct_above_lowest:.2f}%")
        print(f"  Volatility: {signals.volatility_pct:.2f}%")
        print(f"  Claimed discount: {signals.claimed_discount_pct}")
        print(f"  Spike before discount: {signals.spike_before_discount}")

    if not analysis.history.empty:
        prices = analysis.history["current_price_minor"]
        print(f"  First observed price: {_display_price(int(prices.iloc[0]), product.currency)}")
        print(f"  Latest observed price: {_display_price(int(prices.iloc[-1]), product.currency)}")
        print(
            "  Any original price recorded: "
            f"{analysis.history['original_price_minor'].notna().any()}"
            if "original_price_minor" in analysis.history.columns
            else "  Original-price field unavailable"
        )


def report() -> None:
    """Analyze all active products using the API-equivalent history path."""
    database_path = sqlite_url_to_path(settings.database_url)
    if not database_path.is_file():
        raise FileNotFoundError(f"Database does not exist: {database_path}")

    try:
        with SessionLocal() as session:
            product_count = crud.count_products(session)
            products = crud.list_products(session)
            if not products:
                raise RuntimeError(f"No products found in database: {database_path.name}")

            analyses = []
            for product in products:
                history = snapshots_to_dataframe(crud.get_history(session, product.id))
                analyses.append(
                    ProductAnalysis(
                        product=product,
                        history=history,
                        result=compute_trust_score(history),
                    )
                )
    except OperationalError as exc:
        raise RuntimeError(f"Could not read database: {database_path.name}") from exc

    summary = summarize(analyses)
    print(f"Database file: {database_path.name}")
    print(f"Products analyzed: {summary['product_count']} of {product_count}")
    print(f"Total snapshots: {summary['total_snapshots']}")
    print(f"Snapshot-count distribution: {summary['snapshot_counts']}")
    print(f"Products with any recorded original price: {summary['products_with_original_price']}")
    print(f"Label counts: {summary['labels']}")
    print(f"Score counts (excluding None): {summary['scores']}")

    examples = analyses[:2]
    print("\nWorked examples:")
    for analysis in examples:
        _print_example(analysis)


if __name__ == "__main__":
    report()
