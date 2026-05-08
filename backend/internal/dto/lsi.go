package dto

type LSIHistoryPoint struct {
	Date       string  `json:"date"`
	LSI        float64 `json:"lsi"`
	Status     string  `json:"status"`
	Confidence float64 `json:"confidence"`
}

type LSIHistoryResponse struct {
	Points []LSIHistoryPoint `json:"points"`
}

type RecalculateRequest struct {
	Date               string `json:"date"`
	ForceReloadSources bool   `json:"force_reload_sources"`
	RecalculateShap    bool   `json:"recalculate_shap"`
	RegenerateComment  bool   `json:"regenerate_comment"`
}

type RecalculateResponse struct {
	Result         *DashboardResponse `json:"result"`
	UpdatedSources []string           `json:"updated_sources"`
}
