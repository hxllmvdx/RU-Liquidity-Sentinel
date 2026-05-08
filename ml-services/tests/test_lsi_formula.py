from lsi_engine.formula import calculate_base_lsi


def test_calculate_base_lsi():
    assert calculate_base_lsi({"m1": 10.0, "m2": 20.0}) == 15.0
