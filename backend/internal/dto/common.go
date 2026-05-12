package dto

type DateRange struct {
	From string `json:"from"`
	To   string `json:"to"`
}

type NamedValue struct {
	Name  string  `json:"name"`
	Value float64 `json:"value"`
}
