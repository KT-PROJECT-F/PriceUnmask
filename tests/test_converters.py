from datetime import UTC, datetime

import pandas as pd

from backend.converters import (
    HISTORY_COLUMNS,
    product_to_out,
    snapshots_to_dataframe,
)
from backend.db.models import PriceSnapshot, Product


def snap(
    day: int,
    price: int,
    original: int | None = None,
) -> PriceSnapshot:
    return PriceSnapshot(
        scraped_at=datetime(
            2026,
            10,
            day,
            10,
            0,
            tzinfo=UTC,
        ),
        current_price_minor=price,
        original_price_minor=original,
    )


PRODUCT = Product(
    id=1,
    name="Demo Air Fryer",
    url="https://example.com/p/1",
    currency="INR",
)


def test_dataframe_has_exact_columns() -> None:
    df = snapshots_to_dataframe([snap(1, 1000, 1500)])

    assert list(df.columns) == HISTORY_COLUMNS


def test_empty_input_keeps_columns() -> None:
    df = snapshots_to_dataframe([])

    assert df.empty
    assert list(df.columns) == HISTORY_COLUMNS


def test_out_of_order_is_sorted_oldest_first() -> None:
    df = snapshots_to_dataframe(
        [
            snap(3, 900),
            snap(1, 1000),
            snap(2, 950),
        ]
    )

    assert df["current_price_minor"].tolist() == [1000, 950, 900]
    assert df["scraped_at"].is_monotonic_increasing


def test_missing_original_price_stays_missing_and_integer() -> None:
    df = snapshots_to_dataframe(
        [
            snap(1, 1000, 1500),
            snap(2, 900, None),
        ]
    )

    assert df.loc[0, "original_price_minor"] == 1500
    assert pd.isna(df.loc[1, "original_price_minor"])
    assert str(df["original_price_minor"].dtype) == "Int64"
    assert df["current_price_minor"].dtype == "int64"


def test_product_out_latest_and_lowest() -> None:
    out = product_to_out(
        PRODUCT,
        [
            snap(3, 1100),
            snap(1, 1000),
            snap(2, 800),
        ],
    )

    assert out.latest_price_minor == 1100
    assert out.lowest_price_minor == 800
    assert out.trust_label is None


def test_product_out_without_snapshots() -> None:
    out = product_to_out(PRODUCT, [])

    assert out.latest_price_minor is None
    assert out.lowest_price_minor is None
