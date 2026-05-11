from __future__ import annotations

from common.db_models import LSIResult
from pipeline.latest_recalculation import run_latest_recalculation


def test_run_latest_recalculation_returns_structured_result(monkeypatch):
    monkeypatch.setattr("pipeline.latest_recalculation.Database.connect", lambda self: None)
    monkeypatch.setattr("pipeline.latest_recalculation.Database.close", lambda self: None)
    monkeypatch.setattr("pipeline.latest_recalculation.Database.fetch_one", lambda self, query, params=None: {"id": "1"} if "RETURNING *" in query or "SELECT 1 FROM pg_extension" in query else None)
    monkeypatch.setattr("pipeline.latest_recalculation.Database.fetch_all", lambda self, query, params=None: [])
    monkeypatch.setattr("pipeline.latest_recalculation.Database.execute", lambda self, query, params=None: 1)
    monkeypatch.setattr(
        "pipeline.latest_recalculation.BaseParser.run_latest_mode",
        classmethod(lambda cls, parsers=None, db=None, out_dir=None: [type("R", (), {"source_code": "CBR_RUONIA", "status": "success"})()]),
    )
    monkeypatch.setattr("pipeline.latest_recalculation._load_m3_signals", lambda: __import__("pandas").DataFrame())
    monkeypatch.setattr("pipeline.latest_recalculation._load_m5_signals", lambda: __import__("pandas").DataFrame())
    result = run_latest_recalculation()
    assert isinstance(result, LSIResult)
