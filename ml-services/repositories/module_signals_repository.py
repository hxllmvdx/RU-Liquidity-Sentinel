from __future__ import annotations

from datetime import date

from common.database import Database


class ModuleSignalsRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def upsert_signal(self, signal_date: date, module_id: str, signal_name: str, raw_value: float | None = None, mad_score: float | None = None, flag: bool = False, unit: str | None = None, metadata: dict | None = None) -> dict:
        query = """
        INSERT INTO module_signals (signal_date, module_id, signal_name, raw_value, mad_score, flag, unit, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (module_id, signal_name, signal_date) DO UPDATE SET
            raw_value = EXCLUDED.raw_value,
            mad_score = EXCLUDED.mad_score,
            flag = EXCLUDED.flag,
            unit = EXCLUDED.unit,
            metadata = EXCLUDED.metadata
        RETURNING *
        """
        return self.db.fetch_one(query, (signal_date, module_id, signal_name, raw_value, mad_score, flag, unit, metadata)) or {}

    def upsert_many_signals(self, signals: list[dict]) -> list[dict]:
        return [self.upsert_signal(**signal) for signal in signals]

    def get_signals(self, module_id: str, from_date: date, to_date: date) -> list[dict]:
        return self.db.fetch_all(
            """
            SELECT *
            FROM module_signals
            WHERE module_id = %s AND signal_date BETWEEN %s AND %s
            ORDER BY signal_date, signal_name
            """,
            (module_id, from_date, to_date),
        )

    def get_latest_signals(self, module_id: str | None = None) -> list[dict]:
        if module_id:
            query = """
            SELECT DISTINCT ON (signal_name) *
            FROM module_signals
            WHERE module_id = %s
            ORDER BY signal_name, signal_date DESC
            """
            return self.db.fetch_all(query, (module_id,))
        query = """
        SELECT DISTINCT ON (module_id, signal_name) *
        FROM module_signals
        ORDER BY module_id, signal_name, signal_date DESC
        """
        return self.db.fetch_all(query)

    def upsert_active_flag(self, flag_date: date, module_id: str, flag_name: str, description: str | None = None, severity: float | None = None) -> dict:
        query = """
        INSERT INTO active_flags (flag_date, module_id, flag_name, description, severity)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (flag_date, module_id, flag_name) DO UPDATE SET
            description = EXCLUDED.description,
            severity = EXCLUDED.severity
        RETURNING *
        """
        return self.db.fetch_one(query, (flag_date, module_id, flag_name, description, severity)) or {}

    def upsert_many_active_flags(self, flags: list[dict]) -> list[dict]:
        return [self.upsert_active_flag(**flag) for flag in flags]

    def get_active_flags(self, flag_date: date | None = None, module_id: str | None = None) -> list[dict]:
        clauses = ["1=1"]
        params: list = []
        if flag_date:
            clauses.append("flag_date = %s")
            params.append(flag_date)
        if module_id:
            clauses.append("module_id = %s")
            params.append(module_id)
        return self.db.fetch_all(f"SELECT * FROM active_flags WHERE {' AND '.join(clauses)} ORDER BY flag_date, module_id, flag_name", params)

    def clear_active_flags_for_date(self, flag_date: date, module_id: str | None = None) -> int:
        if module_id:
            return self.db.execute("DELETE FROM active_flags WHERE flag_date = %s AND module_id = %s", (flag_date, module_id))
        return self.db.execute("DELETE FROM active_flags WHERE flag_date = %s", (flag_date,))
