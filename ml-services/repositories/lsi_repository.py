from __future__ import annotations

from datetime import date

from common.database import Database


class LSIRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def upsert_lsi_value(self, calculation_date: date, lsi: float, status: str, confidence: float | None = None, auto_comment: str | None = None, model_version: str | None = None) -> dict:
        query = """
        INSERT INTO lsi_values (calculation_date, lsi, status, confidence, auto_comment, model_version)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (calculation_date) DO UPDATE SET
            lsi = EXCLUDED.lsi,
            status = EXCLUDED.status,
            confidence = EXCLUDED.confidence,
            auto_comment = EXCLUDED.auto_comment,
            model_version = EXCLUDED.model_version
        RETURNING *
        """
        return self.db.fetch_one(query, (calculation_date, lsi, status, confidence, auto_comment, model_version)) or {}

    def get_latest_lsi(self) -> dict | None:
        return self.db.fetch_one("SELECT * FROM lsi_values ORDER BY calculation_date DESC LIMIT 1")

    def get_lsi_by_date(self, calculation_date: date) -> dict | None:
        return self.db.fetch_one("SELECT * FROM lsi_values WHERE calculation_date = %s", (calculation_date,))

    def get_lsi_history(self, from_date: date, to_date: date, limit: int = 500, offset: int = 0) -> list[dict]:
        return self.db.fetch_all(
            """
            SELECT *
            FROM lsi_values
            WHERE calculation_date BETWEEN %s AND %s
            ORDER BY calculation_date
            LIMIT %s OFFSET %s
            """,
            (from_date, to_date, limit, offset),
        )

    def upsert_module_contribution(self, lsi_value_id: str, module_id: str, module_name: str, contribution_value: float, contribution_percent: float | None = None) -> dict:
        query = """
        INSERT INTO module_contributions (lsi_value_id, module_id, module_name, contribution_value, contribution_percent)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (lsi_value_id, module_id) DO UPDATE SET
            module_name = EXCLUDED.module_name,
            contribution_value = EXCLUDED.contribution_value,
            contribution_percent = EXCLUDED.contribution_percent
        RETURNING *
        """
        return self.db.fetch_one(query, (lsi_value_id, module_id, module_name, contribution_value, contribution_percent)) or {}

    def upsert_many_module_contributions(self, lsi_value_id: str, contributions: list[dict]) -> list[dict]:
        return [
            self.upsert_module_contribution(
                lsi_value_id=lsi_value_id,
                module_id=item["module_id"],
                module_name=item["module_name"],
                contribution_value=item["contribution_value"],
                contribution_percent=item.get("contribution_percent"),
            )
            for item in contributions
        ]

    def get_module_contributions(self, lsi_value_id: str) -> list[dict]:
        return self.db.fetch_all(
            "SELECT * FROM module_contributions WHERE lsi_value_id = %s ORDER BY contribution_value DESC",
            (lsi_value_id,),
        )

    def update_auto_comment(self, calculation_date: date, auto_comment: str) -> dict | None:
        return self.db.fetch_one(
            "UPDATE lsi_values SET auto_comment = %s WHERE calculation_date = %s RETURNING *",
            (auto_comment, calculation_date),
        )
