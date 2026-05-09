from retriever import retrieve_context

def answer_question(question):
    retrieval_result = retrieve_context(question)
    documents = retrieval_result["documents"]

    if not documents:
        return {
            "answer": "К сожалению, я не нашёл данных для ответа на этот вопрос.",
            "citations": []
        }
    
    context_parts = []
    for doc in documents:
        context_parts.append(
            f"[{doc['source_type']}] {doc['content']}"
        )
    context_text = "\n\n".join(context_parts)
    return {"answer": f"Stub answer for: {question}", "citations": context_text}
