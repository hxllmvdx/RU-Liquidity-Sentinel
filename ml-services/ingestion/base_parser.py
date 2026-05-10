from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ParserRunResult:
    source_code: str
    record_count: int
    output_path: Path
    requested_from: date
    requested_to: date


class BaseParser(ABC):
    source_name = "base"

    @property
    def repo_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def default_out_dir(self) -> Path:
        return self.repo_root / ".." / "data" / "raw"

    @staticmethod
    def utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def default_date_range(days: int = 30) -> tuple[date, date]:
        today = datetime.now(timezone.utc).date()
        return today - timedelta(days=days), today

    @abstractmethod
    def fetch(self, date_from: date, date_to: date):
        raise NotImplementedError
