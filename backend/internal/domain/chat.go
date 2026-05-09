package domain

import (
	"encoding/json"
	"time"

	"github.com/google/uuid"
)

type ChatSession struct {
	ID         uuid.UUID
	SessionKey string
	Title      *string
	CreatedAt  time.Time
	UpdatedAt  time.Time
}

type ChatMessage struct {
	ID        uuid.UUID
	SessionID uuid.UUID
	Role      string
	Content   string
	Contexts  json.RawMessage
	CreatedAt time.Time
}
