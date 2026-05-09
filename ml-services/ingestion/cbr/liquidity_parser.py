from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from bs4 import BeautifulSoup

from ingestion.base_parser import BaseParser, ParserRunResult
from ingestion.cbr.client import CbrClient
from ingestion.cbr.io import write_csv_atomic
from ingestion.cbr.schemas import CbrBankingLiquidityRecord
from ingestion.cbr.utils import parse_russian_date, parse_russian_float


class LiquidityParser(BaseParser):
    source_name = "cbr_liquidity"
    source_code = "CBR_BANKING_LIQUIDITY"
    path = "/hd_base/bliquidity/"

    def __init__(self, client: CbrClient | None = None) -> None:
        self.client = client or CbrClient()

    def fetch(self, date_from: date, date_to: date) -> list[CbrBankingLiquidityRecord]:
        html = self.client.get(self.path, date_from, date_to)
        return self.parse_html(html)

    def parse_html(self, html: str) -> list[CbrBankingLiquidityRecord]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if table is None:
            raise ValueError("CBR liquidity table not found")
        loaded_at = self.utc_now()
        records: list[CbrBankingLiquidityRecord] = []
        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
            if len(cells) < 2:
                continue
            observation_date = parse_russian_date(cells[0])
            if observation_date is None:
                continue
            records.append(
                CbrBankingLiquidityRecord(
                    source_code=self.source_code,
                    observation_date=observation_date,
                    indicator_name="banking_sector_liquidity",
                    value_bln_rub=parse_russian_float(cells[1]),
                    unit="bln_rub",
                    raw={"date": cells[0], "value": cells[1]},
                    loaded_at=loaded_at,
                )
            )
        if not records:
            raise ValueError("CBR liquidity parser returned no records")
        return records

    def run(self, date_from: date, date_to: date, out_dir: Path | None = None) -> ParserRunResult:
        output_root = out_dir or self.default_out_dir
        records = self.fetch(date_from, date_to)
        output_path = output_root / "cbr" / "liquidity" / "normalized" / f"cbr_banking_liquidity_{date_from.isoformat()}_{date_to.isoformat()}.csv"
        write_csv_atomic(records, output_path)
        return ParserRunResult(self.source_code, len(records), output_path, date_from, date_to)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="date_from", default="2014-02-01")
    parser.add_argument("--to", dest="date_to", default="2026-03-02")
    parser.add_argument("--out-dir", dest="out_dir", default="data/raw")
    args = parser.parse_args()
    instance = LiquidityParser()
    result = instance.run(date.fromisoformat(args.date_from), date.fromisoformat(args.date_to), Path(args.out_dir))
    print(result.output_path)


if __name__ == "__main__":
    main()
