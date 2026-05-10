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

    def test_roskazna_cache_only_uses_local_xml(self) -> None:
        parser = EksDepositsParser()
        xml_text = (FIXTURES_DIR / "roskazna" / "eks_sample.xml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp_dir:
            parser._output_root = Path(tmp_dir)
            parser._use_cache_only = True
            source_path = parser.source_files_dir / "20260508_sample.xml"
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_text(xml_text, encoding="utf-8")
            content, status = parser._download_or_load_cached("https://roskazna.gov.ru/storage/operation-day-files/20260508_sample.xml", source_path)

        self.assertIsNotNone(content)
        self.assertEqual(status["status"], "cached")

    def test_roskazna_operation_day_fixture(self) -> None:
        parser = EksDepositsParser()
        html = """
        <table>
          <tr>
            <th>Информация об операциях/Дата</th>
            <th>Показатель</th>
            <th>01.12.2024</th>
            <th>01.12.2024</th>
            <th>02.12.2024</th>
          </tr>
          <tr>
            <td>Размещено на банковских депозитах</td>
            <td>Сумма, млн рублей</td>
            <td>100 000,0</td>
            <td>50 000,0</td>
            <td>75 000,0</td>
          </tr>
        </table>
        """

        records = parser.parse_operation_day_html(html, "https://roskazna.gov.ru/finansovye-operacii/operacionnyj-den/?old=01/12/2024&this=02/12/2024")
        aggregated = parser._aggregate_by_day(records)

        self.assertEqual(len(aggregated), 2)
        self.assertEqual(aggregated[0].observation_date, date(2024, 12, 1))
        self.assertEqual(aggregated[0].placement_volume_bln_rub, 150.0)
        self.assertIsNone(aggregated[0].participant_banks_count)
        self.assertEqual(aggregated[1].observation_date, date(2024, 12, 2))
        self.assertEqual(aggregated[1].placement_volume_bln_rub, 75.0)

    def test_roskazna_operation_day_filters_unexpected_dates(self) -> None:
        parser = EksDepositsParser()
        html = """
        <table>
          <tr>
            <th>Информация об операциях/Дата</th>
            <th>Показатель</th>
            <th>04.05.2026</th>
            <th>05.05.2026</th>
          </tr>
          <tr>
            <td>Размещено на банковских депозитах</td>
            <td>Сумма, млн рублей</td>
            <td>100 000,0</td>
            <td>50 000,0</td>
          </tr>
        </table>
        """

        records = parser.parse_operation_day_html(
            html,
            "https://roskazna.gov.ru/finansovye-operacii/operacionnyj-den/?old=01/01/2012&this=29/04/2012",
            expected_from=date(2012, 1, 1),
            expected_to=date(2012, 4, 29),
        )

        self.assertEqual(records, [])

    def test_roskazna_operation_day_xml_fixture(self) -> None:
        parser = EksDepositsParser()
        xml = """<?xml version="1.0"?>
        <OperDay>
          <Rec Num="1">
            <OperDate>2021-01-11</OperDate>
            <DepoSum>150000000000</DepoSum>
            <DepoCntOrg>3</DepoCntOrg>
          </Rec>
          <Rec Num="2">
            <OperDate>2021-01-11</OperDate>
            <DepoSum>50000000000</DepoSum>
            <DepoCntOrg>4</DepoCntOrg>
          </Rec>
          <Rec Num="3">
            <OperDate>2021-01-12</OperDate>
            <DepoSum/>
            <DepoCntOrg/>
          </Rec>
        </OperDay>
        """

        records = parser.parse_operation_day_xml(
            xml,
            "https://roskazna.gov.ru/finansovye-operacii/operacionnyj-den/",
            expected_from=date(2021, 1, 1),
            expected_to=date(2021, 12, 31),
        )
        aggregated = parser._aggregate_by_day(records)

        self.assertEqual(len(aggregated), 2)
        self.assertEqual(aggregated[0].observation_date, date(2021, 1, 11))
        self.assertEqual(aggregated[0].placement_volume_bln_rub, 200.0)
        self.assertEqual(aggregated[0].participant_banks_count, 4)
        self.assertEqual(aggregated[1].observation_date, date(2021, 1, 12))
        self.assertEqual(aggregated[1].placement_volume_bln_rub, 0.0)

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
                    {"observation_date": "2026-03-01", "value_bln_rub": 2.0, "source_file": "s1.xlsx"},
                    {"observation_date": "2026-04-01", "value_bln_rub": 12.0, "source_file": "s2.xlsx"},
                    {"observation_date": "2026-04-01", "value_bln_rub": 3.0, "source_file": "s2.xlsx"},
                ],
            )
            self._write_csv(
                eks_path,
                [
                    {
                        "observation_date": "2026-04-03",
                        "placement_volume_bln_rub": 5.0,
                        "participant_banks_count": 3,
                        "source_file": "e1.xml",
                    },
                    {
                        "observation_date": "2026-04-17",
                        "placement_volume_bln_rub": 7.0,
                        "participant_banks_count": 4,
                        "source_file": "e2.xml",
                    },
                ],
            )
            self._write_csv(
                liquidity_path,
                [
                    {"observation_date": "2026-03-31", "value_bln_rub": -850.0},
                    {"observation_date": "2026-04-03", "value_bln_rub": -800.0},
                    {"observation_date": "2026-04-17", "value_bln_rub": -780.0},
                ],
            )

            features = build_features_from_files(sors_path, eks_path, liquidity_path)

        self.assertEqual(len(features), 5)
        self.assertEqual(features[0].observation_date, date(2026, 3, 1))
        self.assertEqual(features[1].observation_date, date(2026, 3, 31))
        self.assertEqual(features[2].observation_date, date(2026, 4, 1))
        self.assertEqual(features[3].observation_date, date(2026, 4, 3))
        self.assertEqual(features[4].observation_date, date(2026, 4, 17))
        self.assertEqual(features[0].federal_budget_and_extrabudgetary_funds_balances_bln_rub, 12.0)
        self.assertAlmostEqual(features[1].federal_budget_and_extrabudgetary_funds_balances_bln_rub, 14.903225806451612)
        self.assertEqual(features[2].federal_budget_and_extrabudgetary_funds_balances_bln_rub, 15.0)
        self.assertEqual(features[3].federal_budget_and_extrabudgetary_funds_balances_bln_rub, 15.0)
        self.assertEqual(features[2].delta_month_bln_rub, 3.0)
        self.assertEqual(features[4].delta_week_bln_rub, 0.0)
        self.assertEqual(features[3].eks_deposit_placement_volume_bln_rub, 5.0)
        self.assertEqual(features[4].eks_deposit_placement_volume_bln_rub, 7.0)
        self.assertEqual(features[4].participant_banks_count, 4)
        self.assertEqual(features[4].ground_truth_liquidity_bln_rub, -780.0)

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
