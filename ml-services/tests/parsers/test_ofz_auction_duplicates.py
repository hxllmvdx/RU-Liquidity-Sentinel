import pandas as pd

from ingestion.minfin.ofz_auction_normalizer import split_duplicates


def test_duplicates_split() -> None:
    frame = pd.DataFrame(
        [
            {"auction_date": "2026-05-06", "ofz_issue": "26240RMFS"},
            {"auction_date": "2026-05-06", "ofz_issue": "26240RMFS"},
        ]
    )
    result = split_duplicates(frame)
    assert len(result.deduped) == 1
    assert len(result.conflicts) == 2
