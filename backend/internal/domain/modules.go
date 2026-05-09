package domain

import (
	"encoding/json"
	"time"

	"github.com/google/uuid"
)

type ModuleSignal struct {
	ID         uuid.UUID
	SignalDate time.Time
	ModuleID   string
	SignalName string
	RawValue   *float64
	MADScore   *float64
	Flag       bool
	Unit       *string
	Metadata   json.RawMessage
	CreatedAt  time.Time
}

type ActiveFlag struct {
	ID          uuid.UUID
	FlagDate    time.Time
	ModuleID    string
	FlagName    string
	Description *string
	Severity    *float64
	CreatedAt   time.Time
}

type ModuleContribution struct {
	ID                  uuid.UUID
	LSIValueID          uuid.UUID
	ModuleID            string
	ModuleName          string
	ContributionValue   float64
	ContributionPercent *float64
	CreatedAt           time.Time
}

type ShapValue struct {
	ID          uuid.UUID
	LSIValueID  uuid.UUID
	FeatureName string
	ModuleID    string
	Value       float64
	AbsValue    float64
	CreatedAt   time.Time
}
