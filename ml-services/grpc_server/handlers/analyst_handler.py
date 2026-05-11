from __future__ import annotations

from common.database import Database
from llm.auto_comment import generate_auto_comment
from repositories import RagRepository


def generate_auto_comment_handler(context: dict):
    return {"comment": generate_auto_comment(context)}


def chat_analyst(query: str, limit: int = 5):
    db = Database()
    db.connect()
    contexts = RagRepository(db).search_documents_text(query, limit=limit)
    db.close()
    answer = generate_auto_comment({"query": query, "contexts": contexts})
    return {"answer": answer, "contexts": contexts}
