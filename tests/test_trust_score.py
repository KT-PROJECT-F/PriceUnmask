import pandas as pd
import pytest
from sqlalchemy.orm import Session

from backend.analysis.trust_score import (
    MIN_SNAPSHOTS,
    TrustSignals,
    compute_signals,
    compute_trust_score,
)
from backend.converters import snapshots_to_dataframe
from backend.db.crud import get_history, list_products
from backend.db.models import Product
from backend.devtools.seed_fake_data import DAYS, SNAPSHOTS_PER_DAY, _series, seed


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


def seeded_history(kind: str) -> pd.DataFrame:
    prices = _series(kind, DAYS * SNAPSHOTS_PER_DAY)
    return pd.DataFrame(
        {
            "scraped_at": pd.date_range(
                "2026-10-01 00:00:00+00:00",
                periods=len(prices),
                freq="4h",
            ),
            "current_price_minor": [price for price, _ in prices],
            "original_price_minor": [original for _, original in prices],
        }
    )


@pytest.mark.parametrize(
    ("kind", "expected_label"),
    [
        ("stable", "genuine"),
        ("real_drop", "genuine"),
        ("fake_discount", "likely_inflated"),
    ],
)
def test_compute_trust_score_classifies_seeded_patterns(
    kind: str,
    expected_label: str,
) -> None:
    score = compute_trust_score(seeded_history(kind))

    assert score.label == expected_label
    assert score.score is not None


def test_compute_trust_score_classifies_seeded_database_history(
    session: Session,
) -> None:
    seed(session)

    expected = {
        "Demo Bluetooth Speaker (stable)": "genuine",
        "Demo Running Shoes (real drop)": "genuine",
        "Demo Air Fryer (fake discount)": "likely_inflated",
    }
    products = list_products(session)
    assert {product.name for product in products} == set(expected)

    actual: dict[str, str] = {}
    for product in products:
        snapshots = get_history(session, product.id)
        assert len(snapshots) == DAYS * SNAPSHOTS_PER_DAY

        history = snapshots_to_dataframe(snapshots)
        assert isinstance(history["scraped_at"].dtype, pd.DatetimeTZDtype)
        assert str(history["scraped_at"].dt.tz) == "UTC"
        assert history["current_price_minor"].dtype == "int64"
        assert str(history["original_price_minor"].dtype) == "Int64"

        score = compute_trust_score(history)
        print(f"\nProduct: {product.name}")
        print(f"Label: {score.label}")
        print(f"Score: {score.score}")
        print(f"Reasons: {score.reasons}")
        assert score.reasons
        actual[product.name] = score.label

        if product.name == "Demo Air Fryer (fake discount)":
            reasons = " ".join(score.reasons).casefold()
            assert "rose sharply" in reasons
            assert "advertised discount" in reasons
            assert "volatility" in reasons

    assert actual == expected


def test_compute_trust_score_requires_at_least_six_snapshots() -> None:
    score = compute_trust_score(seeded_history("stable").iloc[: MIN_SNAPSHOTS - 1])

    assert score.score is None
    assert score.label == "insufficient_data"
    assert score.signals is None
    assert score.reasons
    assert "5 price snapshots" in score.reasons[0]
    assert "at least 6" in score.reasons[0]


@pytest.mark.parametrize("kind", ["stable", "real_drop", "fake_discount"])
def test_compute_trust_score_is_bounded_for_seeded_patterns(kind: str) -> None:
    score = compute_trust_score(seeded_history(kind))

    assert score.score is not None
    assert 0 <= score.score <= 100


@pytest.mark.parametrize("kind", ["stable", "real_drop", "fake_discount"])
def test_compute_trust_score_reasons_are_full_sentences(kind: str) -> None:
    score = compute_trust_score(seeded_history(kind))

    assert score.reasons
    assert all(reason.endswith(".") for reason in score.reasons)


def test_compute_trust_score_explains_seeded_fake_discount_warnings() -> None:
    score = compute_trust_score(seeded_history("fake_discount"))

    assert score.label == "likely_inflated"
    assert score.score is not None
    assert score.score < 40
    assert any("rose sharply" in reason for reason in score.reasons)
    assert any("advertised discount" in reason for reason in score.reasons)
    assert any("volatility" in reason for reason in score.reasons)


def daily_history(
    prices: list[int],
    originals: list[int | None] | None = None,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "scraped_at": pd.date_range("2026-10-01", periods=len(prices), tz="UTC"),
            "current_price_minor": prices,
            "original_price_minor": originals if originals is not None else [None] * len(prices),
        }
    )


def test_compute_trust_score_seeded_fake_discount_is_exactly_20() -> None:
    score = compute_trust_score(seeded_history("fake_discount"))

    # 100 - 40 (spike) - 25 (large discount gap) - 15 (high volatility)
    assert score.score == 20
    assert len(score.reasons) == 3


def test_compute_trust_score_without_warnings_is_100_with_one_reason() -> None:
    score = compute_trust_score(daily_history([1000] * 10))

    assert score.score == 100
    assert score.label == "genuine"
    assert score.reasons == ["The recorded prices show no strong signs of an inflated discount."]


@pytest.mark.parametrize(
    ("original", "expected_score"),
    [
        (1198, 100),  # gap rounds to 14.9 points: below the moderate threshold
        (1200, 90),  # gap exactly 15: moderate
        (1490, 90),  # gap rounds to 29.6: still moderate
        (1500, 75),  # gap exactly 30: large
    ],
)
def test_compute_trust_score_discount_gap_thresholds(
    original: int,
    expected_score: int,
) -> None:
    # Earlier typical price 1000, today 900: the real saving is 10%.
    history = daily_history([1000] * 9 + [900], [None] * 9 + [original])

    assert compute_trust_score(history).score == expected_score


@pytest.mark.parametrize(("today", "expected_score"), [(999, 100), (1000, 85)])
def test_compute_trust_score_price_above_lowest_threshold(
    today: int,
    expected_score: int,
) -> None:
    # Lowest price 800: 999 is below 25% above it, 1000 is exactly 25% above.
    history = daily_history([800] + [1000] * 8 + [today])

    assert compute_trust_score(history).score == expected_score


def test_compute_trust_score_high_volatility_costs_15_points() -> None:
    score = compute_trust_score(daily_history([1500, 500] * 5))

    assert score.score == 85
    assert any("volatility" in reason for reason in score.reasons)


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        (0, "Only 0 price snapshots are"),
        (1, "Only 1 price snapshot is"),
        (5, "Only 5 price snapshots are"),
    ],
)
def test_compute_trust_score_insufficient_data_message_grammar(
    rows: int,
    expected: str,
) -> None:
    score = compute_trust_score(daily_history([1000] * rows))

    assert score.label == "insufficient_data"
    assert expected in score.reasons[0]


def test_compute_trust_score_does_not_crash_on_a_zero_price() -> None:
    score = compute_trust_score(daily_history([0, 1000, 1000, 1000, 1000, 1000]))

    assert score.score is not None
    assert 0 <= score.score <= 100


def test_compute_trust_score_spike_alone_costs_40_points() -> None:
    history = daily_history(
        [1000, 1000, 1000, 1600, 1000, 1000],
        [None, None, None, None, None, 1010],
    )
    history["scraped_at"] = pd.to_datetime(
        [
            "2026-10-01 00:00:00+00:00",
            "2026-10-02 00:00:00+00:00",
            "2026-10-03 00:00:00+00:00",
            "2026-10-10 00:00:00+00:00",
            "2026-10-11 00:00:00+00:00",
            "2026-10-12 00:00:00+00:00",
        ]
    )

    score = compute_trust_score(history)

    assert score.score == 60
    assert score.label == "uncertain"
    assert len(score.reasons) == 1
    assert "rose sharply" in score.reasons[0]
