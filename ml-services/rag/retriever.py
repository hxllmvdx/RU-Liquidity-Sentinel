from embeddings import embed_text
import psycopg2
from db import get_cursore

def retrieve_context(query: str, top_k: int =5):
    query_emb = embed_text(query)
    cur = get_cursore()
    
    try:
        cur.execute("""
            SELECT title, source_url, content, metadata,
                1 - (embedding <=> %s::vector) AS similarity
            FROM rag_documents
            ORDER BY similarity DESC
            LIMIT %s
        """, (query_emb, top_k))
        rows = cur.fetchall()


        documents = []
        for row in rows:
            documents.append({
                "title": row[0],
                "source_url": row[1],
                "content": row[2],
                "metadata": row[3],
                "similarity": float(row[4])
            })

        return {"query": query, "top_k": top_k, "documents": documents}
    finally:
        cur.close()
