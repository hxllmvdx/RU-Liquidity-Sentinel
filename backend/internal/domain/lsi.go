package domain

import (
	"time"

	"github.com/google/uuid"
)

type LSIValue struct {
	ID              uuid.UUID
	CalculationDate time.Time
	LSI             float64
	Status          string
	Confidence      *float64
	AutoComment     *string
	ModelVersion    *string
	CalculatedAt    time.Time
	CreatedAt       time.Time
	UpdatedAt       time.Time
}

type LSISnapshot struct {
	Value         LSIValue
	Contributions []ModuleContribution
	ShapValues    []ShapValue
}
