from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from bs4 import BeautifulSoup

from common.db_models import RawFetchResult, RawObservation, SourceStatus
from ingestion.base_parser import BaseParser, ParserRunResult
from ingestion.cbr.client import CbrClient
from ingestion.cbr.io import write_csv_atomic
from ingestion.cbr.schemas import CbrKeyRateRecord
from ingestion.cbr.utils import clean_text, parse_russian_date, parse_russian_float


class RuoniaParser(BaseParser):
    source_name = "cbr_ruonia"
    source_code = "CBR_RUONIA"
    source_url = "https://www.cbr.ru/hd_base/ruonia/dynamics/"
    path = "/hd_base/ruonia/dynamics/"

    def __init__(self, client: CbrClient | None = None, db=None) -> None:
        super().__init__(db=db)
        self.client = client or CbrClient()

    def fetch(self, date_from: date, date_to: date) -> list[CbrKeyRateRecord]:
        html = self.client.get(self.path, date_from, date_to)
        return self.parse_html(html)

    def parse_html(self, html: str) -> list[CbrKeyRateRecord]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.select_one("table.data")
        if table is None:
            raise ValueError("ruonia table not found")
        rows = table.select("tr")
        records: list[CbrKeyRateRecord] = []
        loaded_at = self.utc_now()

        # Current CBR RUONIA page is a transposed table:
        # first row contains dates across columns, second row contains rates.
        if rows:
            header_cells = rows[0].find_all(["td", "th"])
            if len(header_cells) >= 2:
                dates = [
                    parse_russian_date(clean_text(cell.get_text(" ", strip=True)))
                    for cell in header_cells[1:]
                ]
                rate_row = None
                for row in rows[1:]:
                    cells = row.find_all(["td", "th"])
                    if not cells:
                        continue
                    label = clean_text(cells[0].get_text(" ", strip=True)).lower()
                    if "ставка ruonia" in label:
                        rate_row = cells
                        break

                if rate_row is not None:
                    for observation_date, value_cell in zip(dates, rate_row[1:]):
                        if observation_date is None:
                            continue
                        raw_value = clean_text(value_cell.get_text(" ", strip=True))
                        records.append(
                            CbrKeyRateRecord(
                                source_code=self.source_code,
                                observation_date=observation_date,
                                rate_percent=parse_russian_float(raw_value),
                                unit="percent_per_annum",
                                raw={"date": observation_date.isoformat(), "value": raw_value},
                                loaded_at=loaded_at,
                            )
                        )

        # Fallback for the older row-based layout.
        if not records:
            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if len(cells) < 2:
                    continue
                raw_date = clean_text(cells[0].get_text(" ", strip=True))
                raw_value = clean_text(cells[1].get_text(" ", strip=True))
                observation_date = parse_russian_date(raw_date)
                if observation_date is None:
                    continue
                records.append(
                    CbrKeyRateRecord(
                        source_code=self.source_code,
                        observation_date=observation_date,
                        rate_percent=parse_russian_float(raw_value),
                        unit="percent_per_annum",
                        raw={"date": raw_date, "value": raw_value},
                        loaded_at=loaded_at,
                    )
                )
        if not records:
            raise ValueError("ruonia parser produced no records")
        return records

    def fetch_latest(self) -> RawFetchResult:
        date_to = self.utc_now().date()
        date_from = date_to - timedelta(days=14)
        html = self.client.get(self.path, date_from, date_to)
        url = self.client.build_url(self.path, date_from, date_to)
        return RawFetchResult(
            self.source_code,
            url,
            self.utc_now(),
            SourceStatus.SUCCESS,
            html,
            {"date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
        )

    def parse_latest(self, raw: RawFetchResult) -> list[RawObservation]:
        records = self.parse_html(str(raw.content))
        latest_date = max(record.observation_date for record in records)
        return [
            RawObservation(
                source_code=self.source_code,
                observation_date=record.observation_date,
                metric_name="ruonia",
                metric_value=record.rate_percent,
                unit=record.unit,
                raw_payload=record.raw,
            )
            for record in records
            if record.observation_date == latest_date
        ]

    def save(
        self,
        records: list[CbrKeyRateRecord],
        date_from: date,
        date_to: date,
        out_dir: Path | None = None,
        overwrite: bool = True,
    ) -> Path:
        base_dir = Path(out_dir) if out_dir else self.default_out_dir
        output_path = base_dir / "cbr" / "ruonia" / f"cbr_ruonia_{date_from.isoformat()}_{date_to.isoformat()}.csv"
        return write_csv_atomic(records, output_path, overwrite=overwrite)

    def run(
        self,
        date_from: date,
        date_to: date,
        out_dir: Path | None = None,
        overwrite: bool = True,
    ) -> ParserRunResult:
        records = self.fetch(date_from, date_to)
        output_path = self.save(records, date_from, date_to, out_dir=out_dir, overwrite=overwrite)
        latest_date = max((record.observation_date for record in records), default=None)
        return ParserRunResult(
            source_code=self.source_code,
            status=SourceStatus.SUCCESS,
            record_count=len(records),
            output_path=output_path,
            requested_from=date_from,
            requested_to=date_to,
            latest_observation_date=latest_date,
        )

    def run_latest(self, out_dir: Path | None = None) -> ParserRunResult:
        date_to = self.utc_now().date()
        date_from = date_to - timedelta(days=14)
        return self.run(date_from, date_to, out_dir=out_dir)

    def run_historical(self, date_from: date, date_to: date, out_dir: Path | None = None) -> ParserRunResult:
        return self.run(date_from, date_to, out_dir=out_dir)
