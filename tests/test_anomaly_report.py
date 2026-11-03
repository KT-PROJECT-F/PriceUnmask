from datetime import UTC, datetime, timedelta

import pandas as pd

from backend.analysis.anomaly_model import detect_anomalies
from backend.db.models import Product
from backend.devtools.anomaly_report import ProductAnalysis, _print_worked_row


def make_analysis(prices: list[int]) -> ProductAnalysis:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    history = pd.DataFrame(
        {
            "scraped_at": pd.to_datetime(
                [start + timedelta(days=day) for day in range(len(prices))], utc=True
            ),
            "current_price_minor": prices,
            "original_price_minor": [None] * len(prices),
        }
    )
    product = Product(name="Test Book", source="test", currency="GBP")
    return ProductAnalysis(product=product, history=history, result=detect_anomalies(history))


def test_worked_row_flat_window_with_big_change_is_flagged(capsys) -> None:
    analysis = make_analysis([1000] * 5 + [1500])

    _print_worked_row(analysis, prefer_flagged=True)

    output = capsys.readouterr().out
    assert "z: undefined" in output
    assert "Flat-window rule: met" in output
    assert "Model result for this row: FLAGGED" in output


def test_worked_row_small_change_is_not_flagged(capsys) -> None:
    analysis = make_analysis([1000, 1010, 990, 1000, 1005, 1020])

    _print_worked_row(analysis, prefer_flagged=False)

    output = capsys.readouterr().out
    assert "Non-flat rule" in output
    assert "Model result for this row: not flagged" in output


def test_worked_row_reports_when_no_row_matches(capsys) -> None:
    analysis = make_analysis([1000] * 6)

    _print_worked_row(analysis, prefer_flagged=True)

    assert "No scored row matches this example." in capsys.readouterr().out
