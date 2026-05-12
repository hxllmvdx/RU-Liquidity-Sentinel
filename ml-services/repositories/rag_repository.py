from __future__ import annotations

from common.database import Database
from common.db_errors import FeatureUnavailableError


class RagRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    def upsert_document(self, source_type: str, source_id: str | None, title: str, content: str, metadata: dict | None = None, embedding: list[float] | None = None) -> dict:
        query = """
        INSERT INTO rag_documents (source_type, source_id, title, content, metadata, embedding)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING *
        """
        return self.db.fetch_one(query, (source_type, source_id, title, content, metadata, embedding)) or {}

    def get_document(self, document_id: str) -> dict | None:
        return self.db.fetch_one("SELECT * FROM rag_documents WHERE id = %s", (document_id,))

    def search_documents_text(self, query: str, limit: int = 10) -> list[dict]:
        sql = """
        SELECT *, ts_rank_cd(to_tsvector('russian', coalesce(title, '') || ' ' || coalesce(content, '')), plainto_tsquery('russian', %s)) AS rank
        FROM rag_documents
        WHERE to_tsvector('russian', coalesce(title, '') || ' ' || coalesce(content, '')) @@ plainto_tsquery('russian', %s)
        ORDER BY rank DESC, created_at DESC
        LIMIT %s
        """
        return self.db.fetch_all(sql, (query, query, limit))

    def search_documents_by_source(self, source_type: str, source_id: str | None = None, limit: int = 50) -> list[dict]:
        if source_id:
            return self.db.fetch_all(
                "SELECT * FROM rag_documents WHERE source_type = %s AND source_id = %s ORDER BY created_at DESC LIMIT %s",
                (source_type, source_id, limit),
            )
        return self.db.fetch_all(
            "SELECT * FROM rag_documents WHERE source_type = %s ORDER BY created_at DESC LIMIT %s",
            (source_type, limit),
        )

    def search_documents_by_embedding(self, embedding: list[float], limit: int = 10) -> list[dict]:
        has_vector = self.db.fetch_one("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        if has_vector is None:
            raise FeatureUnavailableError("pgvector extension is not enabled")
        return self.db.fetch_all(
            "SELECT *, embedding <=> %s::vector AS distance FROM rag_documents WHERE embedding IS NOT NULL ORDER BY distance ASC LIMIT %s",
            ("[" + ",".join(str(value) for value in embedding) + "]", limit),
        )

    def delete_documents_by_source(self, source_type: str, source_id: str | None = None) -> int:
        if source_id:
            return self.db.execute("DELETE FROM rag_documents WHERE source_type = %s AND source_id = %s", (source_type, source_id))
        return self.db.execute("DELETE FROM rag_documents WHERE source_type = %s", (source_type,))
