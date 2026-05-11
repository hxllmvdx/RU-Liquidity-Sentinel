from __future__ import annotations

import pandas as pd

from normalization.mad_normalizer import rolling_mad_score as _rolling_mad_score


def rolling_mad_score_legacy(values: list[float], window: int = 30) -> list[float]:
    return _rolling_mad_score(pd.Series(values, dtype="float64"), window=window).tolist()


rolling_mad_score = rolling_mad_score_legacy
