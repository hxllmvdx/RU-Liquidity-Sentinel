from __future__ import annotations

from common.database import Database
from lsi_engine.formula import calculate_base_lsi
from lsi_engine.status import resolve_status
from repositories import ModuleSignalsRepository


def run_scenario(shocks: list[dict] | None = None):
    db = Database()
    db.connect()
    signals = ModuleSignalsRepository(db).get_latest_signals()
    db.close()
    base_scores = {}
    for signal in signals:
        if signal.get("mad_score") is None:
            continue
        base_scores.setdefault(signal["module_id"], 0.0)
        base_scores[signal["module_id"]] = max(base_scores[signal["module_id"]], abs(float(signal["mad_score"])))
    base_lsi = calculate_base_lsi({key.lower(): min(value * 20.0, 100.0) for key, value in base_scores.items()})
    scenario_lsi = base_lsi
    for shock in shocks or []:
        scenario_lsi += float(shock.get("delta", 0.0))
    return {"base_lsi": base_lsi, "base_status": resolve_status(base_lsi), "scenario_lsi": scenario_lsi, "scenario_status": resolve_status(scenario_lsi), "delta_lsi": scenario_lsi - base_lsi}
