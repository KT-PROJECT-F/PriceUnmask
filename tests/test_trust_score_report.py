from datetime import UTC, datetime, timedelta

import pandas as pd

from backend.analysis.trust_score import compute_trust_score
from backend.db.models import Product
from backend.devtools.trust_score_report import ProductAnalysis, summarize


def make_analysis(
    prices: list[int],
    original_prices: list[int | None],
) -> ProductAnalysis:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    history = pd.DataFrame(
        {
            "scraped_at": pd.to_datetime(
                [start + timedelta(days=day) for day in range(len(prices))],
                utc=True,
            ),
            "current_price_minor": prices,
            "original_price_minor": original_prices,
        }
    )
    product = Product(name="Test Book", source="test", currency="GBP")
    return ProductAnalysis(
        product=product,
        history=history,
        result=compute_trust_score(history),
    )


def test_summarize_counts_labels_scores_and_original_prices() -> None:
    flat_history = make_analysis([1000] * 6, [None] * 6)
    discounted_history = make_analysis([1200] * 5 + [1000], [None] * 5 + [1500])

    summary = summarize([flat_history, discounted_history])

    assert summary["product_count"] == 2
    assert summary["total_snapshots"] == 12
    assert summary["snapshot_counts"] == {6: 2}
    assert summary["products_with_original_price"] == 1
    assert summary["labels"] == {"genuine": 1, "no_discount": 1}
    assert summary["scores"] == {90: 1}


def test_summarize_excludes_insufficient_scores_from_score_counts() -> None:
    short_history = make_analysis([1000], [None])

    summary = summarize([short_history])

    assert summary["labels"] == {"insufficient_data": 1}
    assert summary["scores"] == {}
