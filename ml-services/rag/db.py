from __future__ import annotations

from common.database import Database


def get_database() -> Database:
    db = Database()
    db.connect()
    return db
