from __future__ import annotations

from datetime import date

from common.database import Database
from repositories import ModuleSignalsRepository


def get_module_signals(module_id: str, from_date: str, to_date: str):
    db = Database()
    db.connect()
    repo = ModuleSignalsRepository(db)
    signals = repo.get_signals(module_id, date.fromisoformat(from_date), date.fromisoformat(to_date))
    flags = repo.get_active_flags(module_id=module_id)
    db.close()
    return {"module_id": module_id, "signals": signals, "active_flags": flags}
