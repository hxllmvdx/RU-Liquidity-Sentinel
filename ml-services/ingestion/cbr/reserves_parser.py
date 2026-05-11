from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import json

import requests

from common.db_models import RawFetchResult, RawObservation, SourceStatus
from ingestion.base_parser import BaseParser, ParserRunResult


class ReservesParser(BaseParser):
    source_name = "cbr_reserves"
    source_code = "CBR_RESERVES"
    source_url = "https://www.cbr.ru/hd_base/RReserves/"

    def __init__(self, db=None) -> None:
        super().__init__(db=db)

    def fetch_latest(self) -> RawFetchResult:
        response = requests.get(self.source_url, timeout=20.0)
        response.raise_for_status()
        return RawFetchResult(self.source_code, self.source_url, self.utc_now(), SourceStatus.SUCCESS, response.text, {"mode": "latest"})

    def parse_latest(self, raw: RawFetchResult) -> list[RawObservation]:
        payload = {}
        try:
            if str(raw.content).strip().startswith("{"):
                payload = json.loads(str(raw.content))
        except json.JSONDecodeError:
            payload = {}
        observation_date = date.today() - timedelta(days=1)
        metrics = [
            ("actual_avg_balances", payload.get("actual_avg_balances"), "bln_rub"),
            ("required_reserves", payload.get("required_reserves"), "bln_rub"),
            ("reserves_spread", payload.get("reserves_spread"), "bln_rub"),
        ]
        return [RawObservation(self.source_code, observation_date, name, float(value), unit, payload) for name, value, unit in metrics if value is not None]

    def run_latest(self, out_dir: Path | None = None) -> ParserRunResult:
        del out_dir
        observations = self.parse_latest(self.fetch_latest())
        latest_date = max((item.observation_date for item in observations), default=None)
        return ParserRunResult(
            source_code=self.source_code,
            status=SourceStatus.SUCCESS if observations else SourceStatus.PARTIAL,
            record_count=len(observations),
            requested_from=latest_date,
            requested_to=latest_date,
            latest_observation_date=latest_date,
        )

    def run_historical(self, date_from: date, date_to: date, out_dir: Path | None = None) -> ParserRunResult:
        del date_from, date_to, out_dir
        return ParserRunResult(
            source_code=self.source_code,
            status=SourceStatus.PARTIAL,
            record_count=0,
            error="Historical reserves parser is not implemented yet.",
        )
