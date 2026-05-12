package domain

import (
	"time"

	"github.com/google/uuid"
)

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
