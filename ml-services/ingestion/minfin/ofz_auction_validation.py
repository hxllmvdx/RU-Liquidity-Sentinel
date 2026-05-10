from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OFZAuctionRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    auction_date: date
    ofz_issue: str = Field(min_length=3)
    offer_volume_bln_rub: float | None = None
    demand_volume_bln_rub: float | None = None
    placement_volume_bln_rub: float | None = None
    revenue_bln_rub: float | None = None
    cover_ratio: float | None = None
    weighted_avg_yield: float | None = None
    yield_curve_spread_bp: float | None = None
    is_undercovered: bool
    is_overcovered: bool
    cbr_confirmed: bool
    source_url: str
    cbr_confirmation_url: str | None = None
    parsed_at: datetime

    @field_validator("ofz_issue")
    @classmethod
    def normalize_issue(cls, value: str) -> str:
        return value.strip().upper()


def validate_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [OFZAuctionRecord.model_validate(record).model_dump(mode="json") for record in records]
