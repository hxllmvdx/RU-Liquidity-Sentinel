package dto

type BacktestRequest struct {
	Episode                string `json:"episode"`
	From                   string `json:"from"`
	To                     string `json:"to"`
	IncludeShap            bool   `json:"include_shap"`
	IncludeModuleBreakdown bool   `json:"include_module_breakdown"`
}

type BacktestMetric struct {
	Name  string  `json:"name"`
	Value float64 `json:"value"`
	Unit  string  `json:"unit"`
}

type BacktestEvent struct {
	Date        string  `json:"date"`
	Title       string  `json:"title"`
	Description string  `json:"description"`
	LSI         float64 `json:"lsi"`
	Status      string  `json:"status"`
}

type BacktestResponse struct {
	Episode              string               `json:"episode"`
	Range                DateRange            `json:"range"`
	LSIHistory           []LSIHistoryPoint    `json:"lsi_history"`
	Metrics              []BacktestMetric     `json:"metrics"`
	Events               []BacktestEvent      `json:"events"`
	AverageContributions []ModuleContribution `json:"average_contributions"`
	Conclusion           string               `json:"conclusion"`
}
