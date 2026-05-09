from datetime import date
from pathlib import Path
import json
import tempfile
import unittest

from ingestion.cbr.io import write_jsonl_atomic
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

    def test_writer_creates_jsonl(self) -> None:
        parser = KeyRateParser()
        html = (FIXTURES_DIR / "keyrate_sample.html").read_text(encoding="utf-8")
        records = parser.parse_html(html)

        with tempfile.TemporaryDirectory() as tmp_dir:
            output = write_jsonl_atomic(records, Path(tmp_dir) / "sample.jsonl")
            lines = output.read_text(encoding="utf-8").splitlines()

        self.assertEqual(len(lines), 2)
        payload = json.loads(lines[0])
        self.assertEqual(payload["source_code"], "CBR_KEYRATE")
        self.assertEqual(payload["observation_date"], "2026-05-08")


if __name__ == "__main__":
    unittest.main()
