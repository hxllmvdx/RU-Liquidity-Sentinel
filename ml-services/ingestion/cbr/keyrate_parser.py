from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import logging

from bs4 import BeautifulSoup

from ingestion.base_parser import BaseParser, ParserRunResult
from ingestion.cbr.client import CbrClient
from ingestion.cbr.exceptions import CbrEmptyResultError, CbrParserError
from ingestion.cbr.io import write_jsonl_atomic
from ingestion.cbr.schemas import CbrKeyRateRecord
from ingestion.cbr.utils import clean_text, parse_russian_date, parse_russian_float


LOGGER = logging.getLogger(__name__)


class KeyRateParser(BaseParser):
    source_name = "cbr_keyrate"
    source_code = "CBR_KEYRATE"
    path = "/hd_base/keyrate/"

    def __init__(self, client: CbrClient | None = None) -> None:
        self.client = client or CbrClient()

    def fetch(self, date_from: date, date_to: date) -> list[CbrKeyRateRecord]:
        html = self.client.get(self.path, date_from, date_to)
        return self.parse_html(html)

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
            / f"cbr_keyrate_{date_from.isoformat()}_{date_to.isoformat()}.jsonl"
        )
        return write_jsonl_atomic(records, output_path, overwrite=overwrite)

    def run(
        self,
        date_from: date,
        date_to: date,
        out_dir: Path | None = None,
        overwrite: bool = True,
    ) -> ParserRunResult:
        records = self.fetch(date_from, date_to)
        output_path = self.save(records, date_from, date_to, out_dir=out_dir, overwrite=overwrite)
        return ParserRunResult(
            source_code=self.source_code,
            record_count=len(records),
            output_path=output_path,
            requested_from=date_from,
            requested_to=date_to,
        )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fetch CBR key rate data into data/raw JSONL")
    parser.add_argument("--from", dest="date_from", help="Start date in YYYY-MM-DD")
    parser.add_argument("--to", dest="date_to", help="End date in YYYY-MM-DD")
    parser.add_argument("--out-dir", dest="out_dir", default=None, help="Output directory root, default is data/raw")
    parser.add_argument("--format", dest="fmt", default="jsonl", choices=["jsonl"], help="Output format")
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
        date_from, date_to = parser.default_date_range(30)
        LOGGER.info("using default keyrate date range from=%s to=%s", date_from.isoformat(), date_to.isoformat())

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
