package models

type Scenario struct {
	HorizonDays int               `json:"horizon_days"`
	Shocks      map[string]float64 `json:"shocks"`
}
