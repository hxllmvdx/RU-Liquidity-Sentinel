from ingestion.minfin.ofz_auction_normalizer import calculate_cover_ratio, is_overcovered, is_undercovered, millions_to_billions, normalize_number
from ingestion.minfin.yield_curve_spread_calculator import add_yield_curve_spread, drop_temporary_fields


def test_normalize_number_russian() -> None:
    assert normalize_number("1 234,56%") == 1234.56


def test_mln_to_bln() -> None:
    assert millions_to_billions("15 000") == 15.0


def test_flags_and_cover_ratio() -> None:
    ratio = calculate_cover_ratio(30.0, 15.0)
    assert ratio == 2.0
    assert is_undercovered(1.19) is True
    assert is_overcovered(2.01) is True


def test_yield_curve_spread_is_computed_from_neighbors() -> None:
    records = [
        {"auction_date": __import__("datetime").date(2026, 1, 1), "ofz_issue": "A", "weighted_avg_yield": 10.0, "_days_to_maturity": 100.0},
        {"auction_date": __import__("datetime").date(2026, 1, 1), "ofz_issue": "B", "weighted_avg_yield": 11.0, "_days_to_maturity": 200.0},
        {"auction_date": __import__("datetime").date(2026, 1, 1), "ofz_issue": "C", "weighted_avg_yield": 12.5, "_days_to_maturity": 300.0},
    ]
    add_yield_curve_spread(records, max_date_distance_days=1, max_maturity_distance_days=1000)
    assert records[1]["yield_curve_spread_bp"] == -25.0
    drop_temporary_fields(records)
    assert "_days_to_maturity" not in records[0]
