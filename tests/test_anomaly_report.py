from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pandas as pd
from sqlalchemy.orm import sessionmaker

import backend.devtools.anomaly_report as anomaly_report
from backend.analysis.anomaly_model import AnomalyResult, detect_anomalies
from backend.db.database import Base, make_engine
from backend.db.models import PriceSnapshot, Product
from backend.devtools.anomaly_report import ProductAnalysis, _print_worked_row


def make_analysis(prices: list[int]) -> ProductAnalysis:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    history = pd.DataFrame(
        {
            "scraped_at": pd.to_datetime(
                [start + timedelta(days=day) for day in range(len(prices))],
                utc=True,
            ),
            "current_price_minor": prices,
            "original_price_minor": [None] * len(prices),
        }
    )
    product = Product(name="Test Book", source="test", currency="GBP")
    return ProductAnalysis(
        product=product,
        history=history,
        result=detect_anomalies(history),
    )


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


def test_report_processes_synthetic_histories_from_sqlite(
    tmp_path,
    monkeypatch,
) -> None:
    database_path = tmp_path / "synthetic.db"
    engine = make_engine(f"sqlite:///{database_path.as_posix()}")
    Base.metadata.create_all(engine)

    histories = {
        "Significant drop": [1000, 1010, 990, 1000, 1000, 800],
        "Significant hike": [1000, 1010, 990, 1000, 1000, 1200],
        "Volatile baseline": [700, 1300, 800, 1200, 1000, 700],
    }

    start = datetime(2026, 1, 1, tzinfo=UTC)

    try:
        with sessionmaker(bind=engine)() as session:
            for name, prices in histories.items():
                product = Product(
                    source="synthetic",
                    external_id=name.lower().replace(" ", "-"),
                    name=name,
                    url=(f"https://example.com/{name.lower().replace(' ', '-')}"),
                    currency="INR",
                    is_active=True,
                    created_at=start,
                    last_seen_at=start + timedelta(days=5),
                )
                session.add(product)
                session.flush()

                for day, price in enumerate(prices):
                    session.add(
                        PriceSnapshot(
                            product_id=product.id,
                            scraped_at=start + timedelta(days=day),
                            current_price_minor=price,
                            original_price_minor=None,
                            in_stock=True,
                        )
                    )

            session.commit()

        monkeypatch.setattr(
            anomaly_report,
            "settings",
            SimpleNamespace(database_url="sqlite:///synthetic.db"),
        )
        monkeypatch.setattr(
            anomaly_report,
            "sqlite_url_to_path",
            lambda _: database_path,
        )
        monkeypatch.setattr(
            anomaly_report,
            "SessionLocal",
            sessionmaker(bind=engine),
        )

        observed_results: list[AnomalyResult] = []
        original_detect = anomaly_report.detect_anomalies

        def recording_detect(history: pd.DataFrame) -> AnomalyResult:
            result = original_detect(history)
            observed_results.append(result)
            return result

        monkeypatch.setattr(
            anomaly_report,
            "detect_anomalies",
            recording_detect,
        )

        anomaly_report.report()

        assert len(observed_results) == 3

        # Products are processed alphabetically by name.
        assert [result.latest_is_anomalous for result in observed_results] == [True, True, False]

    finally:
        engine.dispose()
