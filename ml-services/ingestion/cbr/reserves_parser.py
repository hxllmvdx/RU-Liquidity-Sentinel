from __future__ import annotations

from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup
import requests

from common.db_models import RawFetchResult, RawObservation, SourceStatus
from ingestion.base_parser import BaseParser, ParserRunResult
from ingestion.cbr.utils import clean_text, parse_russian_date, parse_russian_float


class ReservesParser(BaseParser):
    source_name = "cbr_reserves"
    source_code = "CBR_RESERVES"
    source_url = "https://www.cbr.ru/hd_base/RReserves/"

    def __init__(self, db=None) -> None:
        super().__init__(db=db)

    @staticmethod
    def _build_url(date_from: date, date_to: date) -> str:
        return (
            "https://www.cbr.ru/hd_base/RReserves/"
            f"?UniDbQuery.From={date_from.strftime('%d.%m.%Y')}"
            f"&UniDbQuery.To={date_to.strftime('%d.%m.%Y')}"
            "&UniDbQuery.Posted=True"
        )

    def fetch(self, date_from: date, date_to: date) -> RawFetchResult:
        url = self._build_url(date_from, date_to)
        response = requests.get(url, timeout=20.0)
        response.raise_for_status()
        response.encoding = response.encoding or "utf-8"
        return RawFetchResult(
            source_code=self.source_code,
            url=url,
            fetched_at=self.utc_now(),
            status=SourceStatus.SUCCESS,
            content=response.text,
            metadata={"date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
        )

    def parse_html(self, html: str, *, latest_only: bool = False) -> list[RawObservation]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.select_one("table.data")
        if table is None:
            raise ValueError("reserves table not found")

        rows = table.select("tr")
        if len(rows) <= 1:
            return []

        observations: list[RawObservation] = []
        parsed_rows: list[tuple[date, dict[str, float | None]]] = []
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 4:
                continue
            observation_date = parse_russian_date(clean_text(cells[0].get_text(" ", strip=True)))
            if observation_date is None:
                continue
            payload = {
                "actual_avg_balances": parse_russian_float(clean_text(cells[1].get_text(" ", strip=True))),
                "required_reserves": parse_russian_float(clean_text(cells[2].get_text(" ", strip=True))),
                "reserves_on_accounts": parse_russian_float(clean_text(cells[3].get_text(" ", strip=True))),
            }
            payload["reserves_spread"] = (
                None
                if payload["actual_avg_balances"] is None or payload["required_reserves"] is None
                else payload["actual_avg_balances"] - payload["required_reserves"]
            )
            parsed_rows.append((observation_date, payload))

        if latest_only and parsed_rows:
            latest_date = max(item[0] for item in parsed_rows)
            parsed_rows = [item for item in parsed_rows if item[0] == latest_date]

        for observation_date, payload in parsed_rows:
            for metric_name, unit in [
                ("actual_avg_balances", "bln_rub"),
                ("required_reserves", "bln_rub"),
                ("reserves_on_accounts", "bln_rub"),
                ("reserves_spread", "bln_rub"),
            ]:
                value = payload.get(metric_name)
                if value is None:
                    continue
                observations.append(
                    RawObservation(
                        source_code=self.source_code,
                        observation_date=observation_date,
                        metric_name=metric_name,
                        metric_value=float(value),
                        unit=unit,
                        raw_payload=payload,
                    )
                )
        return observations

    def fetch_latest(self) -> RawFetchResult:
        today = self.utc_now().date()
        return self.fetch(date(2004, 9, 1), today)

    def parse_latest(self, raw: RawFetchResult) -> list[RawObservation]:
        return self.parse_html(str(raw.content), latest_only=True)

    def run_latest(self, out_dir: Path | None = None) -> ParserRunResult:
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

    def run_historical(self, date_from: date, date_to: date, out_dir: Path | None = None) -> ParserRunResult:
        del out_dir
        observations = self.parse_html(str(self.fetch(date_from, date_to).content), latest_only=False)
        latest_date = max((item.observation_date for item in observations), default=None)
        return ParserRunResult(
            source_code=self.source_code,
            status=SourceStatus.SUCCESS if observations else SourceStatus.STALE,
            record_count=len(observations),
            requested_from=date_from,
            requested_to=date_to,
            latest_observation_date=latest_date,
        )
