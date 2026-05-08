from common.mad import rolling_mad_score


def normalize(values):
    return rolling_mad_score(values)
