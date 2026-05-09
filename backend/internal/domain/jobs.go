package domain

import (
	"encoding/json"
	"time"

	"github.com/google/uuid"
)

type RecalculationJob struct {
	ID                 uuid.UUID
	RequestedDate      *time.Time
	Status             string
	ForceReloadSources bool
	RecalculateShap    bool
	RegenerateComment  bool
	StartedAt          *time.Time
	FinishedAt         *time.Time
	ErrorMessage       *string
	UpdatedSources     json.RawMessage
	ResultLSIValueID   *uuid.UUID
	CreatedAt          time.Time
	UpdatedAt          time.Time
}
