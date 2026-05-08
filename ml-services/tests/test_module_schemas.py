from modules.m1_reserves.schema import MODULE_SCHEMA


def test_module_schema_has_id():
    assert MODULE_SCHEMA["id"] == "m1"
