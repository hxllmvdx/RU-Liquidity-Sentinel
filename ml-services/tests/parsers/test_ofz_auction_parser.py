from pathlib import Path

from ingestion.minfin.ofz_auction_parser import MinfinOFZAuctionParser
from ingestion.minfin.ofz_auction_source import RawSource


def test_parse_excel_returns_only_auction_dataset_fields() -> None:
    fixture = Path("/tmp/ofz_2026.xlsx")
    parser = MinfinOFZAuctionParser(
        config_path=Path("ml-services/ingestion/minfin/sources.yaml"),
        raw_dir=Path("data/raw"),
    )
    records = parser.parse_excel(
        RawSource(
            section_code="66",
            section_name="annual_tables",
            source_type="excel",
            title="Результаты проведенных аукционов по размещению государственных ценных бумаг в 2026 году",
            detail_url="https://minfin.gov.ru/detail",
            source_url="https://minfin.gov.ru/example.xlsx",
            content=fixture.read_bytes(),
            local_path=fixture,
        )
    )
    assert records
    record = records[0]
    assert set(record) == {
        "auction_date",
        "ofz_issue",
        "offer_volume_bln_rub",
        "demand_volume_bln_rub",
        "placement_volume_bln_rub",
        "cover_ratio",
        "weighted_avg_yield",
        "yield_curve_spread_bp",
        "is_undercovered",
        "is_overcovered",
        "cbr_confirmed",
        "source_url",
        "cbr_confirmation_url",
        "parsed_at",
    }
    assert all(r["ofz_issue"] != "ДРПА" for r in records)
