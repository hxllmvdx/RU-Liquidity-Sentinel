from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import argparse
import logging
import re
import zipfile
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

from ingestion.base_parser import BaseParser, ParserRunResult
from ingestion.cbr.client import CbrClient
from ingestion.cbr.io import write_csv_atomic
from ingestion.cbr.schemas import CbrSorsAttractedFundsRecord
from ingestion.cbr.utils import convert_to_bln_rub, parse_russian_date


LOGGER = logging.getLogger(__name__)
XML_NS = {
    "a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}
TARGET_LINK_TEXT = "Бюджетные средства на счетах кредитных организаций"
TARGET_ROW_PATTERN = re.compile(r"федерального бюджета|внебюджетных фондов", re.I)
INDICATOR_NAME = "federal_budget_and_extrabudgetary_funds_balances_on_commercial_bank_accounts"


@dataclass(slots=True)
class XlsxTable:
    rows: list[list[str | float | None]]


class SorsParser(BaseParser):
    source_name = "cbr_sors"
    source_code = "CBR_SORS_ATTRACTED_FUNDS"

    def __init__(self, client: CbrClient | None = None) -> None:
        self.client = client or CbrClient()
        self._output_root: Path | None = None

    @property
    def source_dir(self) -> Path:
        return (self._output_root or self.default_out_dir) / "cbr" / "sors"

    def discover_budget_xlsx_url(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.find_all("a", href=True):
            text = " ".join(link.get_text(" ", strip=True).split())
            if text == TARGET_LINK_TEXT:
                href = link["href"]
                return href if href.startswith("http") else f"{self.client.base_url}{href}"
        raise ValueError(f"failed to find target CBR SORS link: {TARGET_LINK_TEXT}")

    def fetch(self, date_from: date, date_to: date) -> list[CbrSorsAttractedFundsRecord]:
        html = self.client.session.get(f"{self.client.base_url}/statistics/bank_sector/sors/", timeout=self.client.timeout).text
        xlsx_url = self.discover_budget_xlsx_url(html)
        content = self.client.session.get(xlsx_url, timeout=self.client.timeout).content
        source_path = self.source_dir / "source_files" / f"cbr_sors_budget_{date_to.isoformat()}.xlsx"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(content)
        records = self.parse_workbook(source_path, date_from, date_to)
        return records

    def parse_workbook(self, workbook_path: Path, date_from: date, date_to: date) -> list[CbrSorsAttractedFundsRecord]:
        sheet_name, rows = self._read_sheet_rows(workbook_path, "итого")
        header_dates = [parse_russian_date(str(value)) for value in rows[1][1:]]
        loaded_at = self.utc_now()
        records: list[CbrSorsAttractedFundsRecord] = []

        for row_index, row in enumerate(rows[2:], start=3):
            row_label = str(row[0] or "")
            if not TARGET_ROW_PATTERN.search(row_label):
                continue
            for col_index, raw_value in enumerate(row[1:], start=2):
                observation_date = header_dates[col_index - 2]
                if observation_date is None or not (date_from <= observation_date <= date_to):
                    continue
                numeric = float(raw_value) if raw_value not in (None, "") else None
                value_bln = convert_to_bln_rub(numeric, "млн руб.")
                records.append(
                    CbrSorsAttractedFundsRecord(
                        source_code=self.source_code,
                        observation_date=observation_date,
                        indicator_name=INDICATOR_NAME,
                        value_bln_rub=value_bln,
                        unit="bln_rub",
                        original_unit="млн руб.",
                        source_file=str(workbook_path),
                        sheet_name=sheet_name,
                        raw_cell_refs={"value_cell": f"{self._column_letter(col_index)}{row_index}"},
                        raw={"row_label": row_label.strip(), "column_label": observation_date.strftime("%d.%m.%Y")},
                        loaded_at=loaded_at,
                    )
                )
        if not records:
            raise ValueError(f"no SORS records found in {workbook_path}")
        return records

    def run(self, date_from: date, date_to: date, out_dir: Path | None = None) -> ParserRunResult:
        output_root = out_dir or self.default_out_dir
        self._output_root = output_root
        records = self.fetch(date_from, date_to)
        output_path = output_root / "cbr" / "sors" / "normalized" / f"cbr_sors_attracted_funds_{date_from.isoformat()}_{date_to.isoformat()}.csv"
        write_csv_atomic(records, output_path)
        return ParserRunResult(self.source_code, len(records), output_path, date_from, date_to)

    def _read_sheet_rows(self, workbook_path: Path, target_sheet_name: str) -> tuple[str, list[list[str | float | None]]]:
        with zipfile.ZipFile(workbook_path) as archive:
            shared_strings = self._read_shared_strings(archive)
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
            for sheet in workbook.findall("a:sheets/a:sheet", XML_NS):
                if sheet.attrib["name"].strip().lower() != target_sheet_name.lower():
                    continue
                rel_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
                sheet_xml = ET.fromstring(archive.read(f"xl/{rel_map[rel_id]}"))
                rows = self._extract_rows(sheet_xml, shared_strings)
                return sheet.attrib["name"], rows
        raise ValueError(f"sheet not found: {target_sheet_name}")

    def _read_shared_strings(self, archive: zipfile.ZipFile) -> list[str]:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        return [
            "".join(text.text or "" for text in item.findall(".//a:t", XML_NS))
            for item in root.findall("a:si", XML_NS)
        ]

    def _extract_rows(self, sheet_xml: ET.Element, shared_strings: list[str]) -> list[list[str | float | None]]:
        rows: list[list[str | float | None]] = []
        for row in sheet_xml.findall(".//a:sheetData/a:row", XML_NS):
            values: list[str | float | None] = []
            for cell in row.findall("a:c", XML_NS):
                cell_ref = cell.attrib.get("r", "")
                target_index = self._column_index_from_ref(cell_ref) - 1 if cell_ref else len(values)
                while len(values) < target_index:
                    values.append(None)
                value = cell.find("a:v", XML_NS)
                if value is None:
                    values.append(None)
                    continue
                text = value.text or ""
                if cell.attrib.get("t") == "s":
                    values.append(shared_strings[int(text)])
                else:
                    values.append(float(text))
            rows.append(values)
        return rows

    @staticmethod
    def _column_letter(index: int) -> str:
        result = ""
        while index:
            index, remainder = divmod(index - 1, 26)
            result = chr(65 + remainder) + result
        return result

    @staticmethod
    def _column_index_from_ref(cell_ref: str) -> int:
        letters = "".join(ch for ch in cell_ref if ch.isalpha())
        total = 0
        for letter in letters:
            total = total * 26 + (ord(letter.upper()) - 64)
        return total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="date_from", default="2019-01-01")
    parser.add_argument("--to", dest="date_to", default="2026-05-01")
    parser.add_argument("--out-dir", dest="out_dir", default="data/raw")
    args = parser.parse_args()
    instance = SorsParser()
    result = instance.run(date.fromisoformat(args.date_from), date.fromisoformat(args.date_to), Path(args.out_dir))
    print(result.output_path)


if __name__ == "__main__":
    main()
