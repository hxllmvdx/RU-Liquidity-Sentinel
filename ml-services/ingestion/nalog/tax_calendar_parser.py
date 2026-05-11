from __future__ import annotations

from datetime import date

import requests
from bs4 import BeautifulSoup

from common.db_models import RawFetchResult, RawObservation, SourceStatus
from ingestion.base_parser import BaseParser, ParserRunResult


class TaxCalendarParser(BaseParser):
    source_name = "nalog_tax_calendar"
    source_code = "NALOG_CALENDAR"
    source_url = "https://www.nalog.gov.ru/rn77/taxation/taxes/calendar/"

    def __init__(self, db=None) -> None:
        super().__init__(db=db)

    def fetch_latest(self) -> RawFetchResult:
        response = requests.get(self.source_url, timeout=20.0)
        response.raise_for_status()
        return RawFetchResult(self.source_code, self.source_url, self.utc_now(), SourceStatus.SUCCESS, response.text)

    def parse_latest(self, raw: RawFetchResult) -> list[RawObservation]:
        soup = BeautifulSoup(str(raw.content), "html.parser")
        items = []
        for node in soup.select("time")[:10]:
            dt = node.get("datetime") or node.get_text(" ", strip=True)
            try:
                event_date = date.fromisoformat(dt[:10])
            except ValueError:
                continue
            items.append(
                RawObservation(
                    source_code=self.source_code,
                    observation_date=event_date,
                    metric_name="tax_event",
                    metric_value=None,
                    unit=None,
                    raw_payload={"date": dt, "summary": node.parent.get_text(" ", strip=True)},
                )
            )
        return items

    def run_latest(self, out_dir=None) -> ParserRunResult:
        del out_dir
        observations = self.parse_latest(self.fetch_latest())
        latest_date = max((item.observation_date for item in observations), default=None)
        return ParserRunResult(
            source_code=self.source_code,
            status=SourceStatus.SUCCESS if observations else SourceStatus.STALE,
            record_count=len(observations),
            requested_from=latest_date,
            requested_to=latest_date,
            latest_observation_date=latest_date,
        )

    def run_historical(self, date_from: date, date_to: date, out_dir=None) -> ParserRunResult:
        del out_dir
        observations = [item for item in self.parse_latest(self.fetch_latest()) if date_from <= item.observation_date <= date_to]
        latest_date = max((item.observation_date for item in observations), default=None)
        return ParserRunResult(
            source_code=self.source_code,
            status=SourceStatus.SUCCESS if observations else SourceStatus.STALE,
            record_count=len(observations),
            requested_from=date_from,
            requested_to=date_to,
            latest_observation_date=latest_date,
        )
