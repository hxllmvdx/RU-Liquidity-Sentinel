from __future__ import annotations

import numpy as np


def rolling_mad_score(values: list[float] | np.ndarray, window: int = 30) -> list[float]:
    """Stub for rolling MAD normalization used by module signals."""
    if len(values) == 0:
        return []
    return [0.0 for _ in values]
