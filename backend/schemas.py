"""API request/response models (Pydantic v2). Owner: API track.

These are the contract between the backend and the frontend. The frontend owner
builds against these shapes from day one using mock JSON.
Prices go over the wire as minor units (int); the frontend formats them.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from backend.analysis.anomaly_service import AnomalyStatus
from backend.analysis.trust_score import TrustLabel


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str
    currency: str
    latest_price_minor: int | None
    lowest_price_minor: int | None
    trust_label: TrustLabel | None


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
    label: TrustLabel
    reasons: list[str]
    signals: dict[str, float | int | bool | None] | None
    anomaly_status: AnomalyStatus
    anomaly_result: bool | None
    anomaly_message: str


class ScrapeRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    finished_at: datetime | None
    status: str
    products_seen: int
    error_message: str | None


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorOut(BaseModel):
    error: ErrorDetail


class ProductTrendOut(BaseModel):
    product_id: int
    product_name: str
    currency: str
    first_price_minor: int | None
    latest_price_minor: int | None
    change_minor: int | None
    change_percent: float | None
    direction: Literal["drop", "increase", "unchanged", "insufficient_history"]


class TrendOverviewOut(BaseModel):
    period_days: int
    products_analyzed: int
    products_with_price_drop: int
    products_with_price_increase: int
    products_unchanged: int
    average_change_percent: float | None
    products: list[ProductTrendOut]


class PriceDropOut(BaseModel):
    product_id: int
    status: Literal["insufficient_history", "price_dropped", "no_drop"]
    previous_price_minor: int | None
    current_price_minor: int | None
    drop_amount_minor: int | None
    drop_percent: float | None
