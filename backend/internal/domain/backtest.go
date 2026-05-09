package domain

import (
	"encoding/json"
	"time"

	"github.com/google/uuid"
)

type BacktestResult struct {
	ID                   uuid.UUID
	Episode              string
	RangeFrom            time.Time
	RangeTo              time.Time
	Conclusion           *string
	Metrics              json.RawMessage
	Events               json.RawMessage
	LSIHistory           json.RawMessage
	AverageContributions json.RawMessage
	CreatedAt            time.Time
	UpdatedAt            time.Time
}
