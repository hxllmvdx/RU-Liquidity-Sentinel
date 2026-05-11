from __future__ import annotations

from datetime import datetime

from common.database import Database


class DataSourcesRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def upsert_source(
        self,
        source_code: str,
        name: str,
        url: str,
        source_type: str,
        update_frequency: str | None = None,
        is_active: bool = True,
    ) -> dict:
        query = """
        INSERT INTO data_sources (source_code, name, url, source_type, update_frequency, is_active)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (source_code) DO UPDATE SET
            name = EXCLUDED.name,
            url = EXCLUDED.url,
            source_type = EXCLUDED.source_type,
            update_frequency = EXCLUDED.update_frequency,
            is_active = EXCLUDED.is_active
        RETURNING *
        """
        return self.db.fetch_one(query, (source_code, name, url, source_type, update_frequency, is_active)) or {}

    def update_source_status(
        self,
        source_code: str,
        last_status: str,
        last_loaded_at: datetime | None = None,
        last_error: str | None = None,
    ) -> dict:
        query = """
        UPDATE data_sources
        SET last_status = %s,
            last_loaded_at = COALESCE(%s, last_loaded_at),
            last_error = %s
        WHERE source_code = %s
        RETURNING *
        """
        return self.db.fetch_one(query, (last_status, last_loaded_at, last_error, source_code)) or {}

    def get_source_by_code(self, source_code: str) -> dict | None:
        return self.db.fetch_one("SELECT * FROM data_sources WHERE source_code = %s", (source_code,))

    def list_active_sources(self) -> list[dict]:
        return self.db.fetch_all("SELECT * FROM data_sources WHERE is_active = TRUE ORDER BY source_code")
