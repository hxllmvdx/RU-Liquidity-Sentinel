from __future__ import annotations

from rag.lsi_history_context import load_lsi_history_context
from rag.lsi_rag_indexer import rebuild_lsi_rag_index

try:
    from rag.retriever import retrieve_context
except Exception:  # pragma: no cover
    retrieve_context = None


def answer_question(question: str):
    try:
        rebuild_lsi_rag_index(limit_days=30)
    except Exception:
        pass
    lsi_context = load_lsi_history_context(days=30)
    documents = []
    if retrieve_context is not None:
        try:
            retrieval_result = retrieve_context(question)
            documents = retrieval_result.get("documents", [])
        except Exception:
            documents = []

    context_parts = []
    if lsi_context.get("available"):
        context_parts.append("[lsi_history] " + str(lsi_context["summary"]))
        context_parts.append("[lsi_history_rows] " + str(lsi_context.get("rows", [])[-10:]))
    for doc in documents:
        context_parts.append(f"[{doc.get('source_type', 'document')}] {doc.get('content', '')}")

    context_text = "\n\n".join(context_parts)
    if not context_text:
        return {"answer": "Недостаточно данных для ответа.", "citations": []}

    try:
        from llm.client import LLMClient
        prompt = (
            "Ты аналитик RU Liquidity Sentinel. Отвечай на русском, кратко и строго по контексту. "
            "Если вопрос про LSI, ликвидность, стресс, драйверы, модули, флаги или историю, опирайся только на предоставленные данные.\n\n"
            f"Вопрос: {question}\n\nКонтекст:\n{context_text}"
        )
        answer = LLMClient().generate(prompt).strip()
    except Exception:
        answer = lsi_context.get("summary", "Недостаточно данных для ответа.")
    return {"answer": answer, "citations": context_parts}
