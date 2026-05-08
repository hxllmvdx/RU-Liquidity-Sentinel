from common.mad import rolling_mad_score


def test_mad_returns_same_length():
    values = [1.0, 2.0, 3.0]
    assert len(rolling_mad_score(values)) == len(values)
