package domain

import (
	"encoding/json"
	"time"

	"github.com/google/uuid"
)

type RawObservation struct {
	ID              uuid.UUID
	SourceID        uuid.UUID
	ObservationDate time.Time
	MetricName      string
	MetricValue     *float64
	Unit            *string
	RawPayload      json.RawMessage
	LoadedAt        time.Time
	CreatedAt       time.Time
}

type DataSource struct {
	ID              uuid.UUID
	SourceCode      string
	Name            string
	URL             *string
	SourceType      string
	UpdateFrequency *string
	IsActive        bool
	LastLoadedAt    *time.Time
	LastStatus      *string
	LastError       *string
	CreatedAt       time.Time
	UpdatedAt       time.Time
}
