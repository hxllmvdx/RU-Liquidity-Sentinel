from __future__ import annotations

import pandas as pd


def apply_rolling_window(values: pd.Series, window: int = 30) -> pd.Series:
    return values.rolling(window=window, min_periods=1)
