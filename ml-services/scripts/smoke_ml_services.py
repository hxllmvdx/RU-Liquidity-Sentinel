from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.latest_recalculation import run_latest_recalculation
from pipeline.latest_snapshot import build_latest_snapshot
from lsi_engine.formula import calculate_lsi_from_snapshot


def main() -> None:
    snapshot = build_latest_snapshot(parser_results=[])
    formula = calculate_lsi_from_snapshot(snapshot)
    assert 0.0 <= formula.lsi <= 100.0, formula.lsi
    assert all(key in snapshot for key in ["M1_status", "M2_status", "M3_status", "M4_status", "M5_status"])
    result = run_latest_recalculation(recalculate_shap=False, regenerate_comment=False)
    assert 0.0 <= result.lsi <= 100.0, result.lsi
    dashboard = ROOT.parents[0] / "data" / "processed" / "dashboard" / "lsi_dashboard.csv"
    assert dashboard.exists(), dashboard
    print(json.dumps({"ok": True, "snapshot_keys": len(snapshot), "result": asdict(result)}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
