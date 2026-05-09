from sentence_transformers import SentenceTransformer
from db import get_cursore

encoder = SentenceTransformer('intfloat/multilingual-e5-large')

def save_message_with_embedding(session_id, role, message):
    cur = get_cursore()

    emb = encoder.encode([message], normalize_embeddings=True)[0].tolist()
    try:
        cur.execute("""
            INSERT INTO chat_messages (session_id, role, message, embedding)
            VALUES (%s, %s, %s, %s)
        """, (session_id, role, message, emb))
        cur.connection.commit()
    except:
        cur.close()