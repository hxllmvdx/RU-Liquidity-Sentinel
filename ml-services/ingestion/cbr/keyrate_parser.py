from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
import logging
import re

from bs4 import BeautifulSoup

from common.db_models import RawFetchResult, RawObservation, SourceStatus
from ingestion.base_parser import BaseParser, ParserRunResult
from ingestion.cbr.client import CbrClient
from ingestion.cbr.exceptions import CbrEmptyResultError, CbrParserError
from ingestion.cbr.io import write_csv_atomic
from ingestion.cbr.schemas import CbrKeyRateRecord
from ingestion.cbr.utils import clean_text, parse_russian_date, parse_russian_float


LOGGER = logging.getLogger(__name__)


class KeyRateParser(BaseParser):
    source_name = "cbr_keyrate"
    source_code = "CBR_KEYRATE"
    path = "/hd_base/keyrate/"
    source_url = "https://www.cbr.ru/hd_base/keyrate/"

    def __init__(self, client: CbrClient | None = None, db=None) -> None:
        super().__init__(db=db)
        self.client = client or CbrClient()

    def fetch(self, date_from: date, date_to: date) -> list[CbrKeyRateRecord]:
        html = self.client.get(self.path, date_from, date_to)
        return self.parse_html(html)

    def fetch_latest(self) -> RawFetchResult:
        date_to = self.utc_now().date()
        date_from = date_to - timedelta(days=14)
        url = self.client.build_url(self.path, date_from, date_to)
        html = self.client.get(self.path, date_from, date_to)
        return RawFetchResult(
            source_code=self.source_code,
            url=url,
            fetched_at=self.utc_now(),
            status=SourceStatus.SUCCESS,
            content=html,
            metadata={"date_from": date_from.isoformat(), "date_to": date_to.isoformat()},
        )

    def parse_latest(self, raw: RawFetchResult) -> list[RawObservation]:
        records = self.parse_html(str(raw.content))
        if not records:
            return []
        latest_date = max(record.observation_date for record in records)
        latest_records = [record for record in records if record.observation_date == latest_date]
        return [
            RawObservation(
                source_code=self.source_code,
                observation_date=record.observation_date,
                metric_name="key_rate",
                metric_value=record.rate_percent,
                unit=record.unit,
                raw_payload=record.raw,
            )
            for record in latest_records
        ]

    def discover_available_range(self) -> tuple[date, date]:
        html = self.client.get(self.path, date(2013, 9, 17), self.utc_now().date())
        return self.parse_available_range(html)

    def parse_html(self, html: str) -> list[CbrKeyRateRecord]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.select_one("table.data")
        if table is None:
            raise CbrParserError("keyrate table not found in CBR response")

        rows = table.select("tr")
        if len(rows) <= 1:
            raise CbrEmptyResultError("keyrate table is empty")

        loaded_at = self.utc_now()
        records: list[CbrKeyRateRecord] = []
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            raw_date = clean_text(cells[0].get_text(" ", strip=True))
            raw_rate = clean_text(cells[1].get_text(" ", strip=True))
            observation_date = parse_russian_date(raw_date)
            if observation_date is None:
                LOGGER.warning("skipping keyrate row with empty date: %s", raw_date)
                continue
            records.append(
                CbrKeyRateRecord(
                    source_code=self.source_code,
                    observation_date=observation_date,
                    rate_percent=parse_russian_float(raw_rate),
                    unit="percent_per_annum",
                    raw={"date": raw_date, "rate": raw_rate},
                    loaded_at=loaded_at,
                )
            )

        if not records:
            raise CbrEmptyResultError("keyrate parser produced no records")
        return records

    def parse_available_range(self, html: str) -> tuple[date, date]:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        match = re.search(r"Данные доступны с\s+(\d{2}\.\d{2}\.\d{4})\s+по\s+(\d{2}\.\d{2}\.\d{4})", text)
        if not match:
            raise CbrParserError("keyrate available range not found in CBR response")

        date_from = parse_russian_date(match.group(1))
        date_to = parse_russian_date(match.group(2))
        if date_from is None or date_to is None:
            raise CbrParserError("keyrate available range could not be parsed")
        return date_from, date_to

    def save(
        self,
        records: list[CbrKeyRateRecord],
        date_from: date,
        date_to: date,
        out_dir: Path | None = None,
        overwrite: bool = True,
    ) -> Path:
        base_dir = Path(out_dir) if out_dir else self.default_out_dir
        output_path = (
            base_dir
            / "cbr"
            / "keyrate"
            / f"cbr_keyrate_{date_from.isoformat()}_{date_to.isoformat()}.csv"
        )
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
        return self.run(date_from=date_from, date_to=date_to, out_dir=out_dir)

    def run_historical(self, date_from: date, date_to: date, out_dir: Path | None = None) -> ParserRunResult:
        return self.run(date_from=date_from, date_to=date_to, out_dir=out_dir)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch CBR key rate data into data/raw CSV")
    parser.add_argument("--from", dest="date_from", help="Start date in YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", help="End date in YYYY-MM-DD")
    parser.add_argument("--out-dir", dest="out_dir", default=None, help="Output directory root, default is data/raw")
    parser.add_argument("--format", dest="fmt", default="csv", choices=["csv"], help="Output format")
    parser.add_argument("--no-overwrite", action="store_true", help="Fail if output file already exists")
    return parser


def _parse_iso_date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    args = build_arg_parser().parse_args()
    parser = KeyRateParser()

    if args.date_from and args.date_to:
        date_from = _parse_iso_date(args.date_from)
        date_to = _parse_iso_date(args.date_to)
    else:
        date_from, date_to = parser.discover_available_range()
        LOGGER.info("using full keyrate history from=%s to=%s", date_from.isoformat(), date_to.isoformat())

    result = parser.run(
        date_from=date_from,
        date_to=date_to,
        out_dir=Path(args.out_dir) if args.out_dir else None,
        overwrite=not args.no_overwrite,
    )
    print(result.output_path)
    LOGGER.info("parsed keyrate records=%s output=%s", result.record_count, result.output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
