from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any


class SourceStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    STALE = "stale"
    PARTIAL = "partial"


@dataclass(slots=True)
class RawFetchResult:
    source_code: str
    url: str
    fetched_at: datetime
    status: SourceStatus
    content: str | bytes | None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(slots=True)
class RawObservation:
    source_code: str
    observation_date: date
    metric_name: str
    metric_value: float | None
    unit: str | None = None
    raw_payload: dict[str, Any] | list[Any] | str | None = None


@dataclass(slots=True)
class SaveResult:
    inserted_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0


@dataclass(slots=True)
class ParserRunResult:
    source_code: str
    status: SourceStatus
    latest_observation_date: date | None
    inserted_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LSIResult:
    date: str
    lsi: float
    status: str
    confidence: float | None = None
    auto_comment: str | None = None
    contributions: list[dict[str, Any]] = field(default_factory=list)
    shap_values: list[dict[str, Any]] = field(default_factory=list)
    active_flags: list[dict[str, Any]] = field(default_factory=list)
    forecast: list[dict[str, Any]] = field(default_factory=list)
    updated_sources: list[str] = field(default_factory=list)
