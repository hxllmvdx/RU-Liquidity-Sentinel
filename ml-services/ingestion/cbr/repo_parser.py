from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
import logging

from bs4 import BeautifulSoup

from ingestion.base_parser import BaseParser, ParserRunResult
from ingestion.cbr.client import CbrClient
from ingestion.cbr.exceptions import CbrEmptyResultError, CbrParserError
from ingestion.cbr.io import write_jsonl_atomic
from ingestion.cbr.schemas import CbrRepoAuctionRecord
from ingestion.cbr.utils import (
    clean_text,
    parse_repo_caption_datetime,
    parse_russian_date,
    parse_russian_float,
    parse_russian_int,
)


LOGGER = logging.getLogger(__name__)


class RepoParser(BaseParser):
    source_name = "cbr_repo"
    source_code = "CBR_REPO"
    path = "/hd_base/repo/"

    def __init__(self, client: CbrClient | None = None) -> None:
        self.client = client or CbrClient()

    def fetch(self, date_from: date, date_to: date) -> list[CbrRepoAuctionRecord]:
        listing_html = self.client.get(self.path, date_from, date_to, extra_params={"UniDbQuery.P1": "0"})
        auction_dates = self.parse_listing_dates(listing_html)
        if not auction_dates:
            raise CbrEmptyResultError("repo listing contains no auction dates")

        records: list[CbrRepoAuctionRecord] = []
        for auction_date in auction_dates:
            detail_html = self.client.get(self.path, auction_date, auction_date, extra_params={"UniDbQuery.P1": "0"})
            record = self.parse_detail_html(detail_html)
            if record is None:
                LOGGER.warning("repo detail page produced no record for %s", auction_date.isoformat())
                continue
            records.append(record)

        if not records:
            raise CbrEmptyResultError("repo parser produced no records")
        return records

    def parse_listing_dates(self, html: str) -> list[date]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.select_one("table.data")
        if table is None:
            raise CbrParserError("repo listing table not found in CBR response")

        rows = table.select("tr")
        if len(rows) <= 1:
            raise CbrEmptyResultError("repo listing table is empty")

        dates: list[date] = []
        seen: set[date] = set()
        for row in rows[1:]:
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue
            parsed_date = parse_russian_date(clean_text(cells[2].get_text(" ", strip=True)))
            if parsed_date and parsed_date not in seen:
                seen.add(parsed_date)
                dates.append(parsed_date)
        return dates

    def parse_detail_html(self, html: str) -> CbrRepoAuctionRecord | None:
        soup = BeautifulSoup(html, "html.parser")
        caption = soup.select_one("div.table-caption.gray")
        detail_table = soup.select_one("table.data.without_header.levels")
        if caption is None or detail_table is None:
            raise CbrParserError("repo detail table not found in CBR response")

        observation_date, published_at = parse_repo_caption_datetime(caption.get_text(" ", strip=True))
        if observation_date is None:
            raise CbrParserError("repo detail caption does not contain observation date")

        raw_pairs: dict[str, str] = {}
        for row in detail_table.select("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue
            key = clean_text(cells[0].get_text(" ", strip=True))
            value = clean_text(cells[1].get_text(" ", strip=True))
            raw_pairs[key] = value

        if not raw_pairs:
            return None

        return CbrRepoAuctionRecord(
            source_code=self.source_code,
            observation_date=observation_date,
            published_at=published_at,
            auction_type=raw_pairs.get("Тип аукциона"),
            demand_volume_mln_rub=parse_russian_float(raw_pairs.get("Объем спроса на операции репо, млн руб.")),
            deal_volume_mln_rub=parse_russian_float(raw_pairs.get("Общий объем заключенных сделок репо, млн руб.")),
            cutoff_rate_percent=parse_russian_float(raw_pairs.get("Ставка отсечения, % годовых")),
            weighted_average_rate_percent=parse_russian_float(raw_pairs.get("Средневзвешенная ставка, % годовых")),
            min_declared_rate_percent=parse_russian_float(raw_pairs.get("Минимальная заявленная ставка, % годовых")),
            max_declared_rate_percent=parse_russian_float(raw_pairs.get("Максимальная заявленная ставка, % годовых")),
            deal_volume_within_limit_mln_rub=parse_russian_float(
                raw_pairs.get("Объем заключенных сделок репо в рамках лимита, млн руб.")
            ),
            weighted_average_rate_within_limit_percent=parse_russian_float(
                raw_pairs.get(
                    "Средневзвешенная ставка по заявкам, удовлетворенным в рамках лимита, % годовых"
                )
            ),
            term_days=parse_russian_int(raw_pairs.get("Срок, дни")),
            first_leg_date=parse_russian_date(raw_pairs.get("Дата исполнения первой части сделки")),
            second_leg_date=parse_russian_date(raw_pairs.get("Дата исполнения второй части сделки")),
            unit={"volume": "mln_rub", "rate": "percent_per_annum"},
            raw={"caption": clean_text(caption.get_text(" ", strip=True)), "source_fields": raw_pairs},
            loaded_at=self.utc_now(),
        )

    def save(
        self,
        records: list[CbrRepoAuctionRecord],
        date_from: date,
        date_to: date,
        out_dir: Path | None = None,
        overwrite: bool = True,
    ) -> Path:
        base_dir = Path(out_dir) if out_dir else self.default_out_dir
        output_path = (
            base_dir
            / "cbr"
            / "repo"
            / f"cbr_repo_{date_from.isoformat()}_{date_to.isoformat()}.jsonl"
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
    parser = argparse.ArgumentParser(description="Fetch CBR repo auction data into data/raw JSONL")
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
    parser = RepoParser()

    if args.date_from and args.date_to:
        date_from = _parse_iso_date(args.date_from)
        date_to = _parse_iso_date(args.date_to)
    else:
        date_to = parser.utc_now().date()
        date_from = date_to - timedelta(days=30)
        LOGGER.info("using default repo date range from=%s to=%s", date_from.isoformat(), date_to.isoformat())

    result = parser.run(
        date_from=date_from,
        date_to=date_to,
        out_dir=Path(args.out_dir) if args.out_dir else None,
        overwrite=not args.no_overwrite,
    )
    print(result.output_path)
    LOGGER.info("parsed repo records=%s output=%s", result.record_count, result.output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
