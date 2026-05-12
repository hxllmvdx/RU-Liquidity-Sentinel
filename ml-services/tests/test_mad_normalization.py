from __future__ import annotations

import pandas as pd

from normalization.mad_normalizer import rolling_mad_score


def test_mad_score_does_not_fail_on_zero_mad():
    values = pd.Series([1.0, 1.0, 1.0, 1.0])
    result = rolling_mad_score(values, window=3)
    assert len(result) == 4
    assert result.iloc[-1] == 0.0
