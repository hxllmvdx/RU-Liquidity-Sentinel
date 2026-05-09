from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any


@dataclass(slots=True)
class RoskaznaEksDepositRecord:
    source_code: str
    observation_date: date
    period_from: date | None
    period_to: date | None
    placement_volume_bln_rub: float | None
    participant_banks_count: int | None
    auction_count: int | None
    unit: str
    source_file: str
    raw: dict[str, Any]
    loaded_at: datetime

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["observation_date"] = self.observation_date.isoformat()
        payload["period_from"] = self.period_from.isoformat() if self.period_from else None
        payload["period_to"] = self.period_to.isoformat() if self.period_to else None
        payload["loaded_at"] = self.loaded_at.isoformat()
        return payload
