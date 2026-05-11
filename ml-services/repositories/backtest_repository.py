from __future__ import annotations

from datetime import date

from common.database import Database


class BacktestRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def upsert_backtest_result(self, episode: str, range_from: date, range_to: date, conclusion: str | None = None, metrics: dict | None = None, events: list | None = None, lsi_history: list | None = None, average_contributions: list | None = None) -> dict:
        query = """
        INSERT INTO backtest_results (episode, range_from, range_to, conclusion, metrics, events, lsi_history, average_contributions)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        RETURNING *
        """
        row = self.db.fetch_one(query, (episode, range_from, range_to, conclusion, metrics, events, lsi_history, average_contributions))
        if row:
            return row
        update_query = """
        UPDATE backtest_results
        SET conclusion = %s, metrics = %s, events = %s, lsi_history = %s, average_contributions = %s
        WHERE episode = %s AND range_from = %s AND range_to = %s
        RETURNING *
        """
        return self.db.fetch_one(update_query, (conclusion, metrics, events, lsi_history, average_contributions, episode, range_from, range_to)) or {}

    def get_backtest_result(self, episode: str, range_from: date | None = None, range_to: date | None = None) -> dict | None:
        clauses = ["episode = %s"]
        params: list = [episode]
        if range_from:
            clauses.append("range_from = %s")
            params.append(range_from)
        if range_to:
            clauses.append("range_to = %s")
            params.append(range_to)
        return self.db.fetch_one(f"SELECT * FROM backtest_results WHERE {' AND '.join(clauses)} ORDER BY created_at DESC LIMIT 1", params)

    def list_backtest_results(self) -> list[dict]:
        return self.db.fetch_all("SELECT * FROM backtest_results ORDER BY created_at DESC")
