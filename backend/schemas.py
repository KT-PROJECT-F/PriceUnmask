"""API request/response models (Pydantic v2). Owner: API track.

These are the contract between the backend and the frontend. The frontend owner
builds against these shapes from day one using mock JSON.
Prices go over the wire as minor units (int); the frontend formats them.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str
    currency: str
    latest_price_minor: int | None
    lowest_price_minor: int | None
    trust_label: Literal["genuine", "uncertain", "likely_inflated", "insufficient_data"] | None


class PricePointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scraped_at: datetime
    current_price_minor: int
    original_price_minor: int | None


class HistoryOut(BaseModel):
    product_id: int
    points: list[PricePointOut]


class TrustScoreOut(BaseModel):
    product_id: int
    score: int | None
    label: Literal["genuine", "uncertain", "likely_inflated", "insufficient_data"]
    reasons: list[str]
    signals: dict[str, float | int | bool | None] | None
    anomaly_note: str | None = None


class ScrapeRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    products_seen: int
    error_message: str | None
