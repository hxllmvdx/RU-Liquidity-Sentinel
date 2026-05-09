from datetime import date
from pathlib import Path
import unittest

from ingestion.cbr.schemas import CbrKeyRateRecord
from ingestion.cbr.repo_parser import RepoParser


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "cbr"


class RepoParserTest(unittest.TestCase):
    def test_parse_listing_dates_fixture(self) -> None:
        parser = RepoParser()
        html = (FIXTURES_DIR / "repo_listing_sample.html").read_text(encoding="utf-8")

        dates = parser.parse_listing_dates(html)

        self.assertEqual(dates, [date(2026, 5, 5)])

    def test_parse_detail_fixture(self) -> None:
        parser = RepoParser()
        html = (FIXTURES_DIR / "repo_detail_sample.html").read_text(encoding="utf-8")
        keyrates = [
            CbrKeyRateRecord(
                source_code="CBR_KEYRATE",
                observation_date=date(2026, 4, 25),
                rate_percent=14.0,
                unit="percent_per_annum",
                raw={},
                loaded_at=parser.utc_now(),
            )
        ]

        record = parser.parse_detail_html(html, keyrates)

        assert record is not None
        self.assertEqual(record.source_code, "CBR_REPO")
        self.assertEqual(record.auction_date, date(2026, 5, 5))
        self.assertEqual(record.observation_date, date(2026, 5, 5))
        self.assertEqual(record.published_at.isoformat(), "2026-05-05T13:28:00+03:00")
        self.assertEqual(record.key_rate_percent, 14.0)
        self.assertAlmostEqual(record.rate_spread_to_key_rate_percent, 0.5141, places=4)
        self.assertEqual(record.demand_volume_mln_rub, 5427593.6)
        self.assertAlmostEqual(record.demand_volume_bln_rub, 5427.5936, places=4)
        self.assertEqual(record.deal_volume_mln_rub, 4130000.0)
        self.assertEqual(record.placement_volume_bln_rub, 4130.0)
        self.assertAlmostEqual(record.cover_ratio, 5427593.6 / 4130000.0, places=6)
        self.assertEqual(record.cutoff_rate_percent, 14.5014)
        self.assertEqual(record.weighted_average_rate_percent, 14.5141)
        self.assertEqual(record.min_declared_rate_percent, 14.5001)
        self.assertEqual(record.max_declared_rate_percent, 14.72)
        self.assertEqual(record.term_days, 7)
        self.assertEqual(record.first_leg_date, date(2026, 5, 6))
        self.assertEqual(record.second_leg_date, date(2026, 5, 13))


if __name__ == "__main__":
    unittest.main()
