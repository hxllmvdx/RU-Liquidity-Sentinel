from __future__ import annotations

from common.database import Database


class ShapRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def upsert_shap_value(self, lsi_value_id: str, feature_name: str, module_id: str, value: float, abs_value: float) -> dict:
        query = """
        INSERT INTO shap_values (lsi_value_id, feature_name, module_id, value, abs_value)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (lsi_value_id, feature_name) DO UPDATE SET
            module_id = EXCLUDED.module_id,
            value = EXCLUDED.value,
            abs_value = EXCLUDED.abs_value
        RETURNING *
        """
        return self.db.fetch_one(query, (lsi_value_id, feature_name, module_id, value, abs_value)) or {}

    def upsert_many_shap_values(self, lsi_value_id: str, shap_values: list[dict]) -> list[dict]:
        return [
            self.upsert_shap_value(lsi_value_id, item["feature_name"], item["module_id"], item["value"], item["abs_value"])
            for item in shap_values
        ]

    def get_shap_values(self, lsi_value_id: str, limit: int | None = None) -> list[dict]:
        query = "SELECT * FROM shap_values WHERE lsi_value_id = %s ORDER BY abs_value DESC"
        params: list = [lsi_value_id]
        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)
        return self.db.fetch_all(query, params)

    def get_top_shap_values(self, lsi_value_id: str, limit: int = 10) -> list[dict]:
        return self.get_shap_values(lsi_value_id, limit=limit)

    def delete_shap_values_for_lsi(self, lsi_value_id: str) -> int:
        return self.db.execute("DELETE FROM shap_values WHERE lsi_value_id = %s", (lsi_value_id,))
