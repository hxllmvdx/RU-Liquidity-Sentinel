CREATE TABLE IF NOT EXISTS rag_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    source_type TEXT NOT NULL,
    source_id TEXT,

    title TEXT NOT NULL,
    content TEXT NOT NULL,

    metadata JSONB,

    embedding VECTOR(384),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DROP TRIGGER IF EXISTS trg_rag_documents_set_updated_at ON rag_documents;

CREATE TRIGGER trg_rag_documents_set_updated_at
BEFORE UPDATE ON rag_documents
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();
