from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from common.database import Database
from common.db_models import SourceStatus
from repositories.data_sources_repository import DataSourcesRepository

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ParserRunResult:
    source_code: str
    status: str
    record_count: int = 0
    output_path: Path | None = None
    requested_from: date | None = None
    requested_to: date | None = None
    latest_observation_date: date | None = None
    error: str | None = None
    metadata: dict[str, Any] | None = None


class BaseParser(ABC):
    source_name = "base"
    source_code = "BASE"
    source_url = ""
    source_type = "public_site"

    def __init__(self, db: Database | None = None) -> None:
        self.db = db

    @property
    def repo_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def default_out_dir(self) -> Path:
        return self.repo_root / "data" / "raw"

    @staticmethod
    def utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def default_date_range(days: int = 30) -> tuple[date, date]:
        today = datetime.now(timezone.utc).date()
        return today - timedelta(days=days), today

    def ensure_source_registered(self) -> None:
        if self.db is None:
            return
        DataSourcesRepository(self.db).upsert_source(
            source_code=self.source_code,
            name=self.source_name,
            url=self.source_url,
            source_type=self.source_type,
            is_active=True,
        )

    def update_source_status(self, status: str, *, error: str | None = None) -> None:
        if self.db is None:
            return
        DataSourcesRepository(self.db).update_source_status(
            self.source_code,
            status,
            last_loaded_at=self.utc_now(),
            last_error=error,
        )

    @abstractmethod
    def run_latest(self, out_dir: Path | None = None) -> ParserRunResult:
        raise NotImplementedError

    @abstractmethod
    def run_historical(self, date_from: date, date_to: date, out_dir: Path | None = None) -> ParserRunResult:
        raise NotImplementedError

    @classmethod
    def build_default_parsers(cls, db: Database | None = None) -> list["BaseParser"]:
        from ingestion.cbr.keyrate_parser import KeyRateParser
        from ingestion.cbr.liquidity_parser import LiquidityParser
        from ingestion.cbr.repo_parser import RepoParser
        from ingestion.cbr.reserves_parser import ReservesParser
        from ingestion.cbr.ruonia_parser import RuoniaParser
        from ingestion.cbr.sors_parser import SorsParser
        from ingestion.minfin.ofz_parser import OFZParser
        from ingestion.nalog.tax_calendar_parser import TaxCalendarParser
        from ingestion.roskazna.treasury_parser import TreasuryParser

        return [
            RuoniaParser(db=db),
            KeyRateParser(db=db),
            RepoParser(db=db),
            ReservesParser(db=db),
            LiquidityParser(db=db),
            SorsParser(db=db),
            OFZParser(db=db),
            TaxCalendarParser(db=db),
            TreasuryParser(db=db),
        ]

    @classmethod
    def run_latest_mode(
        cls,
        parsers: list["BaseParser"] | None = None,
        *,
        db: Database | None = None,
        out_dir: Path | None = None,
    ) -> list[ParserRunResult]:
        runner_parsers = parsers or cls.build_default_parsers(db=db)
        results: list[ParserRunResult] = []
        for parser in runner_parsers:
            try:
                parser.ensure_source_registered()
                result = parser.run_latest(out_dir=out_dir)
                parser.update_source_status(result.status, error=result.error)
                results.append(result)
            except Exception as exc:
                LOGGER.exception("latest mode failed for %s", parser.source_code)
                parser.update_source_status(SourceStatus.FAILED, error=str(exc))
                results.append(
                    ParserRunResult(
                        source_code=parser.source_code,
                        status=SourceStatus.FAILED,
                        error=str(exc),
                    )
                )
        return results

    @classmethod
    def run_historical_mode(
        cls,
        date_from: date,
        date_to: date,
        parsers: list["BaseParser"] | None = None,
        *,
        db: Database | None = None,
        out_dir: Path | None = None,
    ) -> list[ParserRunResult]:
        runner_parsers = parsers or cls.build_default_parsers(db=db)
        results: list[ParserRunResult] = []
        for parser in runner_parsers:
            try:
                parser.ensure_source_registered()
                result = parser.run_historical(date_from=date_from, date_to=date_to, out_dir=out_dir)
                parser.update_source_status(result.status, error=result.error)
                results.append(result)
            except Exception as exc:
                LOGGER.exception("historical mode failed for %s", parser.source_code)
                parser.update_source_status(SourceStatus.FAILED, error=str(exc))
                results.append(
                    ParserRunResult(
                        source_code=parser.source_code,
                        status=SourceStatus.FAILED,
                        requested_from=date_from,
                        requested_to=date_to,
                        error=str(exc),
                    )
                )
        return results
