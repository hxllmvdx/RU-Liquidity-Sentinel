from pathlib import Path

from ingestion.minfin.ofz_auction_parser import MinfinOFZAuctionParser
from ingestion.minfin.ofz_auction_source import RawSource


def test_parse_excel_keeps_extended_fields() -> None:
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
    assert "security_type" in record
    assert "cut_off_price_pct" in record
    assert "weighted_avg_price_pct" in record
    assert "revenue_bln_rub" in record
