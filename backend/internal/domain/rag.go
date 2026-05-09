package domain

import (
	"encoding/json"
	"time"

	"github.com/google/uuid"
)

type RAGDocument struct {
	ID         uuid.UUID
	SourceType string
	SourceID   *string
	Title      string
	Content    string
	Metadata   json.RawMessage
	Embedding  []float32
	CreatedAt  time.Time
	UpdatedAt  time.Time
}
