from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any


@dataclass(slots=True)
class CbrKeyRateRecord:
    source_code: str
    observation_date: date
    rate_percent: float | None
    unit: str
    raw: dict[str, Any]
    loaded_at: datetime

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["observation_date"] = self.observation_date.isoformat()
        payload["loaded_at"] = self.loaded_at.isoformat()
        return payload


@dataclass(slots=True)
class CbrRepoAuctionRecord:
    source_code: str
    auction_date: date
    observation_date: date
    published_at: datetime | None
    auction_type: str | None
    key_rate_percent: float | None
    rate_spread_to_key_rate_percent: float | None
    demand_volume_mln_rub: float | None
    demand_volume_bln_rub: float | None
    deal_volume_mln_rub: float | None
    placement_volume_bln_rub: float | None
    cover_ratio: float | None
    cutoff_rate_percent: float | None
    weighted_average_rate_percent: float | None
    min_declared_rate_percent: float | None
    max_declared_rate_percent: float | None
    deal_volume_within_limit_mln_rub: float | None
    weighted_average_rate_within_limit_percent: float | None
    term_days: int | None
    first_leg_date: date | None
    second_leg_date: date | None
    unit: dict[str, str]
    raw: dict[str, Any]
    loaded_at: datetime

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["auction_date"] = self.auction_date.isoformat()
        payload["observation_date"] = self.observation_date.isoformat()
        payload["published_at"] = self.published_at.isoformat() if self.published_at else None
        payload["first_leg_date"] = self.first_leg_date.isoformat() if self.first_leg_date else None
        payload["second_leg_date"] = self.second_leg_date.isoformat() if self.second_leg_date else None
        payload["loaded_at"] = self.loaded_at.isoformat()
        return payload
