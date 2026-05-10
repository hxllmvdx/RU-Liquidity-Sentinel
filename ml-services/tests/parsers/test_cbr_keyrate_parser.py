from datetime import date
from pathlib import Path
import tempfile
import unittest
import csv

from ingestion.cbr.io import write_csv_atomic
from ingestion.cbr.keyrate_parser import KeyRateParser
from ingestion.cbr.utils import parse_russian_date, parse_russian_float


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "cbr"


class CbrParsingHelpersTest(unittest.TestCase):
    def test_parse_russian_float(self) -> None:
        self.assertEqual(parse_russian_float("14,50"), 14.5)
        self.assertEqual(parse_russian_float("5 427 593,6"), 5427593.6)
        self.assertIsNone(parse_russian_float(""))
        self.assertIsNone(parse_russian_float("—"))

    def test_parse_russian_date(self) -> None:
        self.assertEqual(parse_russian_date("08.05.2026"), date(2026, 5, 8))


class KeyRateParserTest(unittest.TestCase):
    def test_parse_available_range(self) -> None:
        parser = KeyRateParser()
        html = """
        <html><body><div class="table-caption">Данные доступны с 17.09.2013 по 08.05.2026.</div></body></html>
        """

        date_from, date_to = parser.parse_available_range(html)

        self.assertEqual(date_from, date(2013, 9, 17))
        self.assertEqual(date_to, date(2026, 5, 8))

    def test_parse_fixture(self) -> None:
        parser = KeyRateParser()
        html = (FIXTURES_DIR / "keyrate_sample.html").read_text(encoding="utf-8")

        records = parser.parse_html(html)

        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].source_code, "CBR_KEYRATE")
        self.assertEqual(records[0].observation_date, date(2026, 5, 8))
        self.assertEqual(records[0].rate_percent, 14.5)
        self.assertEqual(records[0].unit, "percent_per_annum")
        self.assertEqual(records[0].raw["rate"], "14,50")

    def test_writer_creates_csv(self) -> None:
        parser = KeyRateParser()
        html = (FIXTURES_DIR / "keyrate_sample.html").read_text(encoding="utf-8")
        records = parser.parse_html(html)

        with tempfile.TemporaryDirectory() as tmp_dir:
            output = write_csv_atomic(records, Path(tmp_dir) / "sample.csv")
            with output.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["source_code"], "CBR_KEYRATE")
        self.assertEqual(rows[0]["observation_date"], "2026-05-08")
        self.assertEqual(rows[0]["rate_percent"], "14.5")


if __name__ == "__main__":
    unittest.main()
