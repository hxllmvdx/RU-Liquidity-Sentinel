package dto

type ScenarioShock struct {
	FeatureName   string  `json:"feature_name"`
	ModuleID      string  `json:"module_id"`
	Delta         float64 `json:"delta"`
	AbsoluteValue float64 `json:"absolute_value"`
	Unit          string  `json:"unit"`
}

type ScenarioRequest struct {
	BaseDate       string          `json:"base_date"`
	TaxWeekEnabled bool            `json:"tax_week_enabled"`
	Shocks         []ScenarioShock `json:"shocks"`
}

type ScenarioResponse struct {
	BaseDate             string               `json:"base_date"`
	BaseLSI              float64              `json:"base_lsi"`
	BaseStatus           string               `json:"base_status"`
	ScenarioLSI          float64              `json:"scenario_lsi"`
	ScenarioStatus       string               `json:"scenario_status"`
	DeltaLSI             float64              `json:"delta_lsi"`
	ChangedContributions []ModuleContribution `json:"changed_contributions"`
	ScenarioShapValues   []ShapValue          `json:"scenario_shap_values"`
	Explanation          string               `json:"explanation"`
}
