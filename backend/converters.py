"""Turn ORM objects into the shapes analysis and the API need.
Owner: API track.
"""

from collections.abc import Sequence

import pandas as pd

from backend.analysis.trust_score import TrustScore, compute_trust_score
from backend.db.models import PriceSnapshot, Product
from backend.schemas import HistoryOut, PricePointOut, ProductOut

HISTORY_COLUMNS = [
    "scraped_at",
    "current_price_minor",
    "original_price_minor",
]


def snapshots_to_dataframe(
    snapshots: Sequence[PriceSnapshot],
) -> pd.DataFrame:
    df = pd.DataFrame(
        [
            {
                "scraped_at": s.scraped_at,
                "current_price_minor": s.current_price_minor,
                "original_price_minor": s.original_price_minor,
            }
            for s in snapshots
        ],
        columns=HISTORY_COLUMNS,
    )

    df["scraped_at"] = pd.to_datetime(df["scraped_at"], utc=True)
    df["current_price_minor"] = df["current_price_minor"].astype("int64")
    df["original_price_minor"] = df["original_price_minor"].astype("Int64")

    return df.sort_values("scraped_at", ignore_index=True)


def trust_score_for_snapshots(
    snapshots: Sequence[PriceSnapshot],
) -> TrustScore:
    """Calculate the trust score using a product's price snapshots."""
    history_df = snapshots_to_dataframe(snapshots)
    return compute_trust_score(history_df)


def product_to_out(
    product: Product,
    snapshots: Sequence[PriceSnapshot],
) -> ProductOut:
    latest_price_minor = None
    lowest_price_minor = None

    if snapshots:
        latest_price_minor = max(
            snapshots,
            key=lambda s: s.scraped_at,
        ).current_price_minor

        lowest_price_minor = min(s.current_price_minor for s in snapshots)

    trust_score = trust_score_for_snapshots(snapshots)

    return ProductOut(
        id=product.id,
        name=product.name,
        url=product.url,
        currency=product.currency,
        latest_price_minor=latest_price_minor,
        lowest_price_minor=lowest_price_minor,
        trust_label=trust_score.label,
    )


def history_to_out(
    product: Product,
    snapshots: Sequence[PriceSnapshot],
) -> HistoryOut:
    return HistoryOut(
        product_id=product.id,
        points=[PricePointOut.model_validate(snapshot) for snapshot in snapshots],
    )
