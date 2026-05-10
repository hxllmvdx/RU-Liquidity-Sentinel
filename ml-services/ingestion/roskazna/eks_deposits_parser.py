from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date
from pathlib import Path
import re
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

from ingestion.base_parser import BaseParser, ParserRunResult
from ingestion.cbr.io import write_csv_atomic
from ingestion.cbr.utils import convert_to_bln_rub, parse_russian_date
from ingestion.roskazna.client import RoskaznaClient
from ingestion.roskazna.schemas import RoskaznaEksDepositRecord


PAGE_URL = (
    "https://roskazna.gov.ru/finansovye-operacii/razmeshchenie-sredstv-edinogo-kaznachejskogo-scheta/"
    "razmeshchenie-sredstv-edinogo-kaznachejskogo-scheta-na-bankovskih-depozitah"
)
DEFAULT_MIN_DATE = date(1900, 1, 1)


class EksDepositsParser(BaseParser):
    source_name = "roskazna_eks_deposits"
    source_code = "ROSKAZNA_EKS_DEPOSITS"

    def __init__(self, client: RoskaznaClient | None = None) -> None:
        self.client = client or RoskaznaClient()
        self._output_root: Path | None = None

    def fetch(self, date_from: date, date_to: date) -> list[RoskaznaEksDepositRecord]:
        html = self.client.get(PAGE_URL)
        links = self.discover_xml_links(html, date_from, date_to)
        records: list[RoskaznaEksDepositRecord] = []
        for observation_date, url in links:
            content = self.client.get(url)
            source_path = (self._output_root or self.default_out_dir) / "roskazna" / "eks_deposits" / "source_files" / Path(url).name
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_text(content, encoding="utf-8")
            records.extend(self.parse_xml(content, observation_date, source_path))
        return self._aggregate_by_day(records)

    def discover_xml_links(self, html: str, date_from: date, date_to: date) -> list[tuple[date, str]]:
        soup = BeautifulSoup(html, "html.parser")
        links: list[tuple[date, str]] = []
        for link in soup.find_all("a", href=True):
            text = " ".join(link.get_text(" ", strip=True).split())
            title = " ".join((link.get("title") or "").split())
            href = link["href"]
            if not href.lower().endswith(".xml"):
                continue
            label = title or text
            match = re.match(r"(\d{2}\.\d{2}\.\d{4})", label)
            if not match:
                continue
            observation_date = parse_russian_date(match.group(1))
            if observation_date is None or not (date_from <= observation_date <= date_to):
                continue
            full_url = href if href.startswith("http") else f"{self.client.base_url}{href}"
            links.append((observation_date, full_url))
        return links

    def parse_xml(self, xml_text: str, observation_date: date, source_path: Path) -> list[RoskaznaEksDepositRecord]:
        root = ET.fromstring(xml_text)
        loaded_at = self.utc_now()
        records: list[RoskaznaEksDepositRecord] = []
        for node in root:
            raw = {child.tag: (child.text or "").strip() for child in node}
            period_from = parse_russian_date(raw.get("firstdate"))
            period_to = parse_russian_date(raw.get("seconddate"))
            settle_mln = float(raw["totalsettle"]) if raw.get("totalsettle") else None
            participant_banks_count = int(raw["crbidders"]) if raw.get("crbidders") else None
            records.append(
                RoskaznaEksDepositRecord(
                    source_code=self.source_code,
                    observation_date=observation_date,
                    period_from=period_from,
                    period_to=period_to,
                    placement_volume_bln_rub=convert_to_bln_rub(settle_mln, "млн руб."),
                    participant_banks_count=participant_banks_count,
                    auction_count=1,
                    unit="bln_rub",
                    source_file=str(source_path),
                    raw=raw,
                    loaded_at=loaded_at,
                )
            )
        return records

    def _aggregate_by_day(self, records: list[RoskaznaEksDepositRecord]) -> list[RoskaznaEksDepositRecord]:
        grouped: dict[date, list[RoskaznaEksDepositRecord]] = defaultdict(list)
        for record in records:
            grouped[record.observation_date].append(record)
        aggregated: list[RoskaznaEksDepositRecord] = []
        for observation_date in sorted(grouped):
            day_records = grouped[observation_date]
            aggregated.append(
                RoskaznaEksDepositRecord(
                    source_code=self.source_code,
                    observation_date=observation_date,
                    period_from=min((r.period_from for r in day_records if r.period_from), default=None),
                    period_to=max((r.period_to for r in day_records if r.period_to), default=None),
                    placement_volume_bln_rub=sum(r.placement_volume_bln_rub or 0 for r in day_records),
                    participant_banks_count=max((r.participant_banks_count for r in day_records if r.participant_banks_count is not None), default=None),
                    auction_count=sum(r.auction_count or 0 for r in day_records),
                    unit="bln_rub",
                    source_file=",".join(r.source_file for r in day_records),
                    raw={"original_fields": [r.raw for r in day_records]},
                    loaded_at=day_records[0].loaded_at,
                )
            )
        return aggregated

    def run(self, date_from: date, date_to: date, out_dir: Path | None = None) -> ParserRunResult:
        output_root = out_dir or self.default_out_dir
        self._output_root = output_root
        records = self.fetch(date_from, date_to)
        output_path = output_root / "roskazna" / "eks_deposits" / "normalized" / f"roskazna_eks_deposits_{date_from.isoformat()}_{date_to.isoformat()}.csv"
        write_csv_atomic(records, output_path)
        return ParserRunResult(self.source_code, len(records), output_path, date_from, date_to)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="date_from")
    parser.add_argument("--to", dest="date_to")
    parser.add_argument("--out-dir", dest="out_dir", default="data/raw")
    args = parser.parse_args()
    instance = EksDepositsParser()
    date_from = date.fromisoformat(args.date_from) if args.date_from else DEFAULT_MIN_DATE
    date_to = date.fromisoformat(args.date_to) if args.date_to else instance.utc_now().date()
    result = instance.run(date_from, date_to, Path(args.out_dir))
    print(result.output_path)


if __name__ == "__main__":
    main()
