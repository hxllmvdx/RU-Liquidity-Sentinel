from __future__ import annotations

from common.database import Database
from llm.auto_comment import generate_auto_comment
from rag.analyst_service import answer_question
from rag.lsi_rag_indexer import rebuild_lsi_rag_index
from repositories import RagRepository


def generate_auto_comment_handler(context: dict):
    return {"comment": generate_auto_comment(context)}


def chat_analyst(query: str, limit: int = 5):
    rebuild_lsi_rag_index(limit_days=30)
    db = Database()
    db.connect()
    try:
        contexts = RagRepository(db).search_documents_text(query, limit=limit)
    finally:
        db.close()
    result = answer_question(query)
    return {"answer": result.get("answer", ""), "contexts": contexts or []}
