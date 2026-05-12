from __future__ import annotations

from common.db_errors import DatabaseQueryError
from rag.db import get_database
from repositories.rag_repository import RagRepository


def retrieve_context(query: str, top_k: int = 5) -> dict:
    db = get_database()
    try:
        repo = RagRepository(db)
        try:
            documents = repo.search_documents_text(query, limit=top_k)
        except DatabaseQueryError:
            documents = []
        return {
            "query": query,
            "top_k": top_k,
            "documents": [
                {
                    "source_type": item.get("source_type", ""),
                    "source_id": item.get("source_id"),
                    "title": item.get("title", ""),
                    "content": item.get("content", ""),
                    "metadata": item.get("metadata") or {},
                }
                for item in documents
            ],
        }
    finally:
        db.close()
