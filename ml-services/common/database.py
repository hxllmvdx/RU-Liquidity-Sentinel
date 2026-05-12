from __future__ import annotations

from contextlib import contextmanager
import json
from typing import Any, Iterator, Sequence

from psycopg import Connection, connect as psycopg_connect
from psycopg.rows import dict_row
from psycopg.types.json import Json

from common.config import Settings
from common.db_errors import (
    DatabaseConnectionError,
    DatabaseQueryError,
    DatabaseTransactionError,
)


class Database:
    def __init__(self, dsn: str | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or Settings()
        self.dsn = dsn or self.settings.resolved_database_url
        self.connection: Connection | None = None

    def connect(self) -> Connection:
        if self.connection is not None and not self.connection.closed:
            return self.connection
        try:
            self.connection = psycopg_connect(self.dsn, row_factory=dict_row)
            self.connection.autocommit = False
            return self.connection
        except Exception as exc:  # pragma: no cover
            raise DatabaseConnectionError(f"Failed to connect to PostgreSQL: {exc}") from exc

    def close(self) -> None:
        if self.connection is not None and not self.connection.closed:
            self.connection.close()
        self.connection = None

    @contextmanager
    def transaction(self) -> Iterator[Connection]:
        connection = self.connect()
        try:
            yield connection
            connection.commit()
        except Exception as exc:
            try:
                connection.rollback()
            except Exception as rollback_exc:  # pragma: no cover
                raise DatabaseTransactionError(f"Rollback failed: {rollback_exc}") from rollback_exc
            if isinstance(exc, DatabaseQueryError):
                raise
            raise DatabaseTransactionError(str(exc)) from exc

    def _normalize_params(self, params: Sequence[Any] | dict[str, Any] | None) -> Any:
        if params is None:
            return None
        if isinstance(params, dict):
            return {key: Json(value) if isinstance(value, (dict, list)) else value for key, value in params.items()}
        return tuple(Json(value) if isinstance(value, (dict, list)) else value for value in params)

    def execute(self, query: str, params: Sequence[Any] | dict[str, Any] | None = None) -> int:
        try:
            with self.connect().cursor() as cursor:
                cursor.execute(query, self._normalize_params(params))
                return cursor.rowcount
        except Exception as exc:
            raise DatabaseQueryError(str(exc)) from exc

    def fetch_one(self, query: str, params: Sequence[Any] | dict[str, Any] | None = None) -> dict[str, Any] | None:
        try:
            with self.connect().cursor() as cursor:
                cursor.execute(query, self._normalize_params(params))
                return cursor.fetchone()
        except Exception as exc:
            raise DatabaseQueryError(str(exc)) from exc

    def fetch_all(self, query: str, params: Sequence[Any] | dict[str, Any] | None = None) -> list[dict[str, Any]]:
        try:
            with self.connect().cursor() as cursor:
                cursor.execute(query, self._normalize_params(params))
                return list(cursor.fetchall())
        except Exception as exc:
            raise DatabaseQueryError(str(exc)) from exc

    def execute_many(self, query: str, params_seq: Sequence[Sequence[Any] | dict[str, Any]]) -> int:
        try:
            normalized = [self._normalize_params(params) for params in params_seq]
            with self.connect().cursor() as cursor:
                cursor.executemany(query, normalized)
                return cursor.rowcount
        except Exception as exc:
            raise DatabaseQueryError(str(exc)) from exc

    def health_check(self) -> dict[str, Any]:
        row = self.fetch_one("SELECT now() AS db_time, current_database() AS database_name")
        return {"ok": row is not None, **(row or {})}

    @staticmethod
    def dumps_json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, default=str)
