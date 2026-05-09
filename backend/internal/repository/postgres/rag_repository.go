package postgres

import (
	"context"
	"fmt"
	"time"

	"github.com/ru-liquidity-sentinel/backend/internal/domain"
)

type RAGRepository struct {
	db *DB
}

func NewRAGRepository(db *DB) *RAGRepository {
	return &RAGRepository{db: db}
}

func (r *RAGRepository) UpsertDocument(ctx context.Context, document domain.RAGDocument) error {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	const query = `INSERT INTO rag_documents (source_type, source_id, title, content, metadata, embedding)
	VALUES ($1, $2, $3, $4, $5, $6)`

	if _, err := r.db.conn.ExecContext(ctx, query,
		document.SourceType,
		document.SourceID,
		document.Title,
		document.Content,
		document.Metadata,
		document.Embedding,
	); err != nil {
		return fmt.Errorf("upsert document: %w", err)
	}

	return nil
}

func (r *RAGRepository) SearchDocuments(ctx context.Context, queryText string, limit int) ([]domain.RAGDocument, error) {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	const query = `SELECT id, source_type, source_id, title, content, metadata, created_at, updated_at
	FROM rag_documents
	WHERE title ILIKE '%' || $1 || '%' OR content ILIKE '%' || $1 || '%'
	ORDER BY updated_at DESC
	LIMIT $2`

	var rows []ragDocumentRow
	if err := r.db.conn.SelectContext(ctx, &rows, query, queryText, limit); err != nil {
		return nil, fmt.Errorf("search documents: %w", err)
	}

	results := make([]domain.RAGDocument, 0, len(rows))
	for _, row := range rows {
		results = append(results, row.toDomain())
	}
	return results, nil
}

func (r *RAGRepository) SearchDocumentsByEmbedding(ctx context.Context, embedding []float32, limit int) ([]domain.RAGDocument, error) {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	const query = `SELECT id, source_type, source_id, title, content, metadata, embedding, created_at, updated_at
	FROM rag_documents
	ORDER BY embedding <-> $1
	LIMIT $2`

	var rows []ragDocumentRow
	if err := r.db.conn.SelectContext(ctx, &rows, query, embedding, limit); err != nil {
		return nil, fmt.Errorf("search documents by embedding: %w", err)
	}

	results := make([]domain.RAGDocument, 0, len(rows))
	for _, row := range rows {
		results = append(results, row.toDomain())
	}
	return results, nil
}
