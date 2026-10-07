import pandas as pd
import pytest
from sqlalchemy.orm import Session

from backend.analysis.trust_score import TrustSignals, compute_signals
from backend.db.models import Product
from backend.devtools.seed_fake_data import seed


def test_compute_signals_basic_history() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.to_datetime(
                [
                    "2026-10-01 10:00:00+00:00",
                    "2026-10-02 10:00:00+00:00",
                    "2026-10-03 10:00:00+00:00",
                    "2026-10-04 10:00:00+00:00",
                    "2026-10-05 10:00:00+00:00",
                ]
            ),
            "current_price_minor": [1000, 900, 1100, 800, 1000],
            "original_price_minor": [1500, 1500, 1500, 1500, 1500],
        }
    )

    signals = compute_signals(history)

    assert signals.snapshot_count == 5
    assert signals.days_of_history == 4
    assert signals.lowest_price_minor == 800
    assert signals.pct_above_lowest == 25.0

    # Check the exact expected value based on your implementation.
    # mean 960, sample std ≈ 114.02 -> 114.02 / 960 ≈ 11.877%
    assert signals.volatility_pct == pytest.approx(11.877, abs=0.001)
    assert type(signals.pct_above_lowest) is float
    assert type(signals.volatility_pct) is float


def test_compute_signals_constant_price() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.to_datetime(
                [
                    "2026-10-01 10:00:00+00:00",
                    "2026-10-02 10:00:00+00:00",
                    "2026-10-03 10:00:00+00:00",
                ]
            ),
            "current_price_minor": [1000, 1000, 1000],
            "original_price_minor": [1500, 1500, 1500],
        }
    )

    signals = compute_signals(history)

    assert signals.lowest_price_minor == 1000
    assert signals.pct_above_lowest == 0.0
    assert signals.volatility_pct == 0.0


def test_compute_signals_single_row() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.to_datetime(["2026-10-01 10:00:00+00:00"]),
            "current_price_minor": [1000],
            "original_price_minor": [1500],
        }
    )

    signals = compute_signals(history)

    assert signals.snapshot_count == 1
    assert signals.days_of_history == 0
    assert signals.lowest_price_minor == 1000
    assert signals.pct_above_lowest == 0.0
    assert signals.volatility_pct == 0.0


def test_compute_signals_today_is_lowest() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.to_datetime(
                [
                    "2026-10-01 10:00:00+00:00",
                    "2026-10-02 10:00:00+00:00",
                    "2026-10-03 10:00:00+00:00",
                    "2026-10-04 10:00:00+00:00",
                ]
            ),
            "current_price_minor": [1000, 1200, 1100, 800],
            "original_price_minor": [1500, 1500, 1500, 1500],
        }
    )

    signals = compute_signals(history)

    assert signals.lowest_price_minor == 800
    assert signals.pct_above_lowest == 0.0


def test_compute_signals_empty_history() -> None:
    history = pd.DataFrame(
        columns=[
            "scraped_at",
            "current_price_minor",
            "original_price_minor",
        ]
    )

    with pytest.raises(ValueError, match="history must contain at least one row"):
        compute_signals(history)


def test_compute_signals_detects_recent_spike_before_sale() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.date_range("2026-09-30", periods=11, tz="UTC"),
            "current_price_minor": [
                1000,
                1000,
                1000,
                1000,
                3000,
                3000,
                1050,
                1050,
                1050,
                1050,
                1050,
            ],
            "original_price_minor": [None] * 10 + [3500],
        }
    )

    signals = compute_signals(history)

    assert signals.spike_before_discount is True
    assert signals.spike_pct == pytest.approx(200.0)


def test_compute_signals_reports_spike_without_current_strikethrough() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.date_range("2026-09-30", periods=11, tz="UTC"),
            "current_price_minor": [
                1000,
                1000,
                1000,
                1000,
                3000,
                3000,
                1050,
                1050,
                1050,
                1050,
                1050,
            ],
            "original_price_minor": [None] * 11,
        }
    )

    signals = compute_signals(history)

    assert signals.spike_pct == pytest.approx(200.0)
    assert signals.spike_before_discount is False


@pytest.mark.parametrize(
    ("recent_price", "expected_spike"),
    [(1499, False), (1500, True)],
)
def test_compute_signals_spike_threshold_boundary(
    recent_price: int,
    expected_spike: bool,
) -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.to_datetime(
                [
                    "2026-09-20 00:00:00+00:00",
                    "2026-09-29 00:00:00+00:00",
                    "2026-09-30 00:00:00+00:00",
                ]
            ),
            "current_price_minor": [1000, recent_price, 1000],
            "original_price_minor": [None, None, 2000],
        }
    )

    signals = compute_signals(history)

    assert signals.spike_pct == pytest.approx(recent_price / 1000 * 100 - 100)
    assert signals.spike_before_discount is expected_spike


def test_compute_signals_long_running_sale_keeps_pre_sale_spike() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.to_datetime(
                [
                    "2026-09-10 00:00:00+00:00",
                    "2026-09-18 00:00:00+00:00",
                    "2026-09-19 00:00:00+00:00",
                    "2026-09-20 00:00:00+00:00",
                    "2026-09-29 00:00:00+00:00",
                ]
            ),
            "current_price_minor": [1000, 3000, 1050, 1050, 1050],
            "original_price_minor": [None, None, 3500, 3500, 3500],
        }
    )

    signals = compute_signals(history)

    assert signals.spike_before_discount is True
    assert signals.spike_pct == pytest.approx(200.0)


def test_compute_signals_stable_price_with_small_sale_has_no_spike() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.date_range("2026-10-01", periods=10, tz="UTC"),
            "current_price_minor": [2000] * 9 + [1900],
            "original_price_minor": [None] * 9 + [2100],
        }
    )

    signals = compute_signals(history)

    assert signals.spike_before_discount is False
    assert signals.spike_pct == 0.0


def test_compute_signals_no_strikethrough_price_has_no_claimed_discount() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.date_range("2026-10-01", periods=2, tz="UTC"),
            "current_price_minor": [1000, 900],
            "original_price_minor": [None, None],
        }
    )

    signals = compute_signals(history)

    assert signals.claimed_discount_pct is None


def test_compute_signals_calculates_claimed_discount_from_latest_row() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.date_range("2026-10-01", periods=2, tz="UTC"),
            "current_price_minor": [2000, 1500],
            "original_price_minor": [2500, 3000],
        }
    )

    signals = compute_signals(history)

    assert signals.claimed_discount_pct == 50.0


def test_compute_signals_ignores_original_price_below_current_price() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.date_range("2026-10-01", periods=2, tz="UTC"),
            "current_price_minor": [2000, 1500],
            "original_price_minor": [None, 1000],
        }
    )

    signals = compute_signals(history)

    assert signals.claimed_discount_pct is None


def test_compute_signals_real_discount_uses_median_of_earlier_prices() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.date_range("2026-10-01", periods=5, tz="UTC"),
            "current_price_minor": [2000, 2100, 1900, 2000, 1000],
            "original_price_minor": [None] * 5,
        }
    )

    signals = compute_signals(history)

    assert signals.real_discount_vs_median_pct == 50.0


def test_compute_signals_real_discount_is_zero_when_price_exceeds_prior_median() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.date_range("2026-10-01", periods=5, tz="UTC"),
            "current_price_minor": [2000, 2100, 1900, 2000, 2500],
            "original_price_minor": [None] * 5,
        }
    )

    signals = compute_signals(history)

    assert signals.real_discount_vs_median_pct == 0.0


def test_compute_signals_spike_is_not_reported_without_enough_history() -> None:
    history = pd.DataFrame(
        {
            "scraped_at": pd.date_range("2026-10-01", periods=3, tz="UTC"),
            "current_price_minor": [1000, 2000, 1000],
            "original_price_minor": [None, None, 1500],
        }
    )

    signals = compute_signals(history)

    assert signals.spike_before_discount is False
    assert signals.spike_pct is None


def test_compute_signals_detects_seeded_fake_discount_but_not_stable_product(
    session: Session,
) -> None:
    seed(session)
    products = {product.name: product for product in session.query(Product).all()}

    def signals_for(product_name: str) -> TrustSignals:
        product = products[product_name]
        history = pd.DataFrame(
            [
                {
                    "scraped_at": snapshot.scraped_at,
                    "current_price_minor": snapshot.current_price_minor,
                    "original_price_minor": snapshot.original_price_minor,
                }
                for snapshot in product.snapshots
            ]
        )
        return compute_signals(history)

    fake_discount = signals_for("Demo Air Fryer (fake discount)")
    stable = signals_for("Demo Bluetooth Speaker (stable)")

    assert fake_discount.spike_before_discount is True
    assert fake_discount.spike_pct is not None
    assert fake_discount.spike_pct >= 50.0
    assert stable.spike_before_discount is False
