import numpy as np
import pandas as pd

from backend.analysis.anomaly_model import _rolling_zscore


def test_rolling_zscore_uses_previous_prices():
    prices = pd.Series([100, 102, 101, 103, 102, 110])
    result = _rolling_zscore(prices, window=5)
    assert result.iloc[:5].isna().all()
    assert result.iloc[5] > 0


def test_rolling_zscore_preserves_index_and_length():
    prices = pd.Series(
        [100, 101, 102, 103, 104, 105],
        index=["a", "b", "c", "d", "e", "f"],
    )
    result = _rolling_zscore(prices, window=5)
    assert len(result) == len(prices)
    assert result.index.equals(prices.index)


def test_rolling_zscore_returns_nan_without_enough_history():
    prices = pd.Series([100, 101, 102, 103, 104])
    result = _rolling_zscore(prices, window=5)
    assert result.isna().all()


def test_rolling_zscore_flat_prices_do_not_produce_infinity():
    prices = pd.Series([100, 100, 100, 100, 100, 100])
    result = _rolling_zscore(prices, window=5)
    assert not np.isinf(result).any()


def test_rolling_zscore_detects_obvious_spike():
    prices = pd.Series([100, 102, 98, 101, 99, 120])
    result = _rolling_zscore(prices, window=5)
    assert result.iloc[-1] > 3
