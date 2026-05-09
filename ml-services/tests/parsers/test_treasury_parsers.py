from __future__ import annotations

from datetime import date
from pathlib import Path
import tempfile
import unittest
import zipfile
import csv

from ingestion.cbr.io import write_csv_atomic
from ingestion.cbr.liquidity_parser import LiquidityParser
from ingestion.cbr.sors_parser import SorsParser
from ingestion.cbr.utils import convert_to_bln_rub, parse_russian_date, parse_russian_float
from ingestion.roskazna.eks_deposits_parser import EksDepositsParser
from modules.m5_treasury.features import build_features_from_files


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"


class TreasuryHelpersTest(unittest.TestCase):
    def test_parse_russian_float(self) -> None:
        self.assertEqual(parse_russian_float("1 234,5"), 1234.5)
        self.assertEqual(parse_russian_float("5 427 593,6"), 5427593.6)
        self.assertIsNone(parse_russian_float("—"))
        self.assertIsNone(parse_russian_float(""))
        self.assertIsNone(parse_russian_float("н/д"))

    def test_parse_russian_date(self) -> None:
        self.assertEqual(parse_russian_date("01.04.2026"), date(2026, 4, 1))
        self.assertEqual(parse_russian_date("апрель 2026"), date(2026, 4, 1))

    def test_convert_to_bln_rub(self) -> None:
        self.assertEqual(convert_to_bln_rub(1000, "млн руб."), 1.0)
        self.assertEqual(convert_to_bln_rub(1_000_000, "тыс. руб."), 1.0)
        self.assertEqual(convert_to_bln_rub(1_000_000_000, "руб."), 1.0)
        self.assertEqual(convert_to_bln_rub(1.0, "млрд руб."), 1.0)


class TreasuryParsersTest(unittest.TestCase):
    def test_cbr_sors_parser_fixture(self) -> None:
        parser = SorsParser()
        with tempfile.TemporaryDirectory() as tmp_dir:
            workbook_path = Path(tmp_dir) / "sample.xlsx"
            self._create_sors_fixture_xlsx(workbook_path)
            records = parser.parse_workbook(workbook_path, date(2026, 4, 1), date(2026, 4, 1))

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].observation_date, date(2026, 4, 1))
        self.assertEqual(records[0].source_file, str(workbook_path))
        self.assertEqual(records[0].sheet_name, "итого")
        self.assertEqual(records[0].value_bln_rub, 1.5)

    def test_roskazna_parser_fixture(self) -> None:
        parser = EksDepositsParser()
        xml_text = (FIXTURES_DIR / "roskazna" / "eks_sample.xml").read_text(encoding="utf-8")
        records = parser.parse_xml(xml_text, date(2026, 5, 8), Path("fixture.xml"))
        aggregated = parser._aggregate_by_day(records)

        self.assertEqual(len(aggregated), 1)
        self.assertEqual(aggregated[0].observation_date, date(2026, 5, 8))
        self.assertAlmostEqual(aggregated[0].placement_volume_bln_rub, 125.952, places=6)
        self.assertEqual(aggregated[0].participant_banks_count, 4)
        self.assertEqual(aggregated[0].auction_count, 2)

    def test_cbr_liquidity_parser_fixture(self) -> None:
        parser = LiquidityParser()
        html = (FIXTURES_DIR / "cbr" / "liquidity_sample.html").read_text(encoding="utf-8")
        records = parser.parse_html(html)

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].observation_date, date(2026, 3, 2))
        self.assertEqual(records[0].value_bln_rub, -850.0)

    def test_treasury_feature_builder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            eks_path = tmp / "eks.csv"
            liquidity_path = tmp / "liquidity.csv"
            sors_path = tmp / "sors.csv"

            self._write_csv(
                sors_path,
                [
                    {"observation_date": "2026-03-01", "value_bln_rub": 10.0, "source_file": "s1.xlsx"},
                    {"observation_date": "2026-04-01", "value_bln_rub": 12.0, "source_file": "s2.xlsx"},
                ],
            )
            self._write_csv(
                eks_path,
                [
                    {
                        "observation_date": "2026-04-01",
                        "placement_volume_bln_rub": 5.0,
                        "participant_banks_count": 3,
                        "source_file": "e1.xml",
                    }
                ],
            )
            self._write_csv(liquidity_path, [{"observation_date": "2026-03-31", "value_bln_rub": -850.0}])

            features = build_features_from_files(sors_path, eks_path, liquidity_path)

        self.assertEqual(len(features), 2)
        self.assertIsNone(features[0].delta_month_bln_rub)
        self.assertEqual(features[1].delta_month_bln_rub, 2.0)
        self.assertIsNone(features[1].delta_week_bln_rub)
        self.assertEqual(features[1].participant_banks_count, 3)
        self.assertEqual(features[1].ground_truth_liquidity_bln_rub, -850.0)

    def test_writer_creates_csv(self) -> None:
        parser = LiquidityParser()
        html = (FIXTURES_DIR / "cbr" / "liquidity_sample.html").read_text(encoding="utf-8")
        records = parser.parse_html(html)
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = write_csv_atomic(records, Path(tmp_dir) / "sample.csv")
            with output.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["observation_date"], "2026-03-02")

    def _write_csv(self, path: Path, rows: list[dict]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def _create_sors_fixture_xlsx(self, path: Path) -> None:
        shared_strings = [
            "01.04.2026",
            "Остатки бюджетных средств на счетах, всего",
            "   средства федерального бюджета",
            "   средства внебюджетных фондов",
            "Остатки  бюджетных средств на счетах, открытых в кредитных организациях в рублях, иностранной валюте и драгоценных металлах (федерального бюджета, бюджетов субъектов Российской Федерации и местных бюджетов, прочих бюджетных средств и средств внебюджетных фондов), млн руб.",
        ]
        workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="итого" sheetId="1" r:id="rId1"/></sheets></workbook>"""
        rels_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>"""
        shared_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="5" uniqueCount="5">""" + "".join(f"<si><t>{value}</t></si>" for value in shared_strings) + "</sst>"
        sheet_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>
<row r="1"><c r="A1" t="s"><v>4</v></c></row>
<row r="2"><c r="B2" t="s"><v>0</v></c></row>
<row r="3"><c r="A3" t="s"><v>1</v></c><c r="B3"><v>1000</v></c></row>
<row r="4"><c r="A4" t="s"><v>2</v></c><c r="B4"><v>1500</v></c></row>
<row r="5"><c r="A5" t="s"><v>3</v></c><c r="B5"><v>250</v></c></row>
</sheetData></worksheet>"""
        content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
</Types>"""
        root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>"""
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("[Content_Types].xml", content_types)
            archive.writestr("_rels/.rels", root_rels)
            archive.writestr("xl/workbook.xml", workbook_xml)
            archive.writestr("xl/_rels/workbook.xml.rels", rels_xml)
            archive.writestr("xl/sharedStrings.xml", shared_xml)
            archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


if __name__ == "__main__":
    unittest.main()
