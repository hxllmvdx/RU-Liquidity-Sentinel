from ingestion.minfin.ofz_auction_normalizer import calculate_cover_ratio, is_overcovered, is_undercovered, millions_to_billions, normalize_number


def test_normalize_number_russian() -> None:
    assert normalize_number("1 234,56%") == 1234.56


def test_mln_to_bln() -> None:
    assert millions_to_billions("15 000") == 15.0


def test_flags_and_cover_ratio() -> None:
    ratio = calculate_cover_ratio(30.0, 15.0)
    assert ratio == 2.0
    assert is_undercovered(1.19) is True
    assert is_overcovered(2.01) is True
