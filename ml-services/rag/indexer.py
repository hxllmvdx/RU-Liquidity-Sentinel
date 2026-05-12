from sentence_transformers import SentenceTransformer
import json
from db import get_cursor
from psycopg2.extras import execute_values
from embeddings import embed_text

encoder = SentenceTransformer('intfloat/multilingual-e5-large')

def index_documents(documents):
    if not documents:
        return 0

    embeddings = [embed_text(doc["content"]) for doc in documents]
    # embeddings – список списков по 1536 чисел
    values = []
    for doc, emb in zip(documents, embeddings):
        values.append((
            doc.get("title", ""),
            doc.get("source_url", ""),
            doc["content"],
            emb,
            json.dumps(doc.get("metadata", {}))
        ))
    cur = get_cursor()
    try:
        execute_values(cur, """
            INSERT INTO rag_documents (title, source_url, content, embedding, metadata)
            VALUES %s
        """, values)
        cur.connection.commit()
        return len(documents)
    finally:
        cur.close()

    
