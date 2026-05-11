from __future__ import annotations

import pandas as pd


def _resolve_window_length(series: pd.Series, window: int | str) -> int:
    if isinstance(window, int):
        return max(window, 1)
    normalized = str(window).upper()
    if normalized.endswith("Y"):
        return max(int(normalized[:-1]) * 52, 1)
    if normalized.endswith("M"):
        return max(int(normalized[:-1]) * 4, 1)
    return 30


def rolling_mad_score(series: pd.Series, window: int | str) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    window_length = _resolve_window_length(values, window)

    def _mad(chunk: pd.Series) -> float:
        non_null = chunk.dropna()
        if non_null.empty:
            return float("nan")
        median = non_null.median()
        mad = (non_null - median).abs().median()
        return float(mad) if pd.notna(mad) and mad != 0 else float("nan")

    rolling_median = values.rolling(window=window_length, min_periods=3).median()
    rolling_mad = values.rolling(window=window_length, min_periods=3).apply(lambda arr: _mad(pd.Series(arr)), raw=False)
    score = 0.6745 * (values - rolling_median) / rolling_mad

    expanding_median = values.expanding(min_periods=3).median()
    expanding_mad = values.expanding(min_periods=3).apply(lambda arr: _mad(pd.Series(arr)), raw=False)
    fallback = 0.6745 * (values - expanding_median) / expanding_mad

    return score.fillna(fallback).replace([float("inf"), float("-inf")], pd.NA).fillna(0.0)
