package postgres

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/ru-liquidity-sentinel/backend/internal/domain"
)

type ChatRepository struct {
	db *DB
}

func NewChatRepository(db *DB) *ChatRepository {
	return &ChatRepository{db: db}
}

func (r *ChatRepository) CreateOrGetSession(ctx context.Context, sessionKey string, title *string) (*domain.ChatSession, error) {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	const query = `INSERT INTO chat_sessions (session_key, title)
	VALUES ($1, $2)
	ON CONFLICT (session_key) DO UPDATE SET
		title = COALESCE(EXCLUDED.title, chat_sessions.title)
	RETURNING id, session_key, title, created_at, updated_at`

	var row chatSessionRow
	if err := r.db.conn.GetContext(ctx, &row, query, sessionKey, title); err != nil {
		return nil, fmt.Errorf("create or get session: %w", err)
	}

	result := row.toDomain()
	return &result, nil
}

func (r *ChatRepository) SaveMessage(ctx context.Context, message domain.ChatMessage) error {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	const query = `INSERT INTO chat_messages (session_id, role, content, contexts)
	VALUES ($1, $2, $3, $4)`

	if _, err := r.db.conn.ExecContext(ctx, query, message.SessionID, message.Role, message.Content, message.Contexts); err != nil {
		return fmt.Errorf("save message: %w", err)
	}

	return nil
}

func (r *ChatRepository) GetSessionMessages(ctx context.Context, sessionID uuid.UUID) ([]domain.ChatMessage, error) {
	ctx, cancel := context.WithTimeout(ctx, 10*time.Second)
	defer cancel()

	const query = `SELECT id, session_id, role, content, contexts, created_at
	FROM chat_messages
	WHERE session_id = $1
	ORDER BY created_at ASC`

	var rows []chatMessageRow
	if err := r.db.conn.SelectContext(ctx, &rows, query, sessionID); err != nil {
		return nil, fmt.Errorf("get session messages: %w", err)
	}

	results := make([]domain.ChatMessage, 0, len(rows))
	for _, row := range rows {
		results = append(results, row.toDomain())
	}
	return results, nil
}
