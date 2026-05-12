from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any


MODULE_SCHEMA = {"id": "m5", "name": "Federal Treasury Funds"}


@dataclass(slots=True)
class M5TreasuryFeatureRecord:
    source_code: str
    observation_date: date
    federal_budget_and_extrabudgetary_funds_balances_bln_rub: float | None
    eks_deposit_placement_volume_bln_rub: float | None
    delta_week_bln_rub: float | None
    delta_month_bln_rub: float | None
    participant_banks_count: int | None
    ground_truth_liquidity_bln_rub: float | None
    raw_refs: dict[str, Any]
    loaded_at: datetime

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["observation_date"] = self.observation_date.isoformat()
        payload["loaded_at"] = self.loaded_at.isoformat()
        return payload
