from __future__ import annotations

from datetime import date

from common.database import Database
from pipeline.latest_recalculation import run_latest_recalculation
from repositories import LSIRepository


def get_current_lsi(auto_recalculate: bool = True):
    db = Database()
    db.connect()
    repo = LSIRepository(db)
    latest = repo.get_latest_lsi()
    db.close()
    if latest is None and auto_recalculate:
        return run_latest_recalculation()
    if latest is None:
        raise RuntimeError("No LSI data available in PostgreSQL")
    return latest


def get_lsi_history(from_date: str, to_date: str, limit: int = 500, offset: int = 0):
    db = Database()
    db.connect()
    rows = LSIRepository(db).get_lsi_history(date.fromisoformat(from_date), date.fromisoformat(to_date), limit=limit, offset=offset)
    db.close()
    return rows


def recalculate_lsi(date_value: str | None = None, force_reload_sources: bool = False, recalculate_shap: bool = True, regenerate_comment: bool = True):
    return run_latest_recalculation(date=date_value, force_reload_sources=force_reload_sources, recalculate_shap=recalculate_shap, regenerate_comment=regenerate_comment)
