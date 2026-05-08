package models

type ModuleSignal struct {
	ID              string  `json:"id"`
	Name            string  `json:"name"`
	RawValue        float64 `json:"raw_value"`
	NormalizedValue float64 `json:"normalized_value"`
	Contribution    float64 `json:"contribution"`
	Status          string  `json:"status"`
}
