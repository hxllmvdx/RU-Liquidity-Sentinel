package models

type LSI struct {
	AsOfDate string  `json:"as_of_date"`
	Value    float64 `json:"value"`
	Status   string  `json:"status"`
}
