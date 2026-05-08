package dto

type DashboardResponse struct {
	Date          string               `json:"date"`
	LSI           float64              `json:"lsi"`
	Status        string               `json:"status"`
	Confidence    float64              `json:"confidence"`
	Contributions []ModuleContribution `json:"contributions"`
	ShapValues    []ShapValue          `json:"shap_values"`
	ActiveFlags   []ActiveFlag         `json:"active_flags"`
	Forecast      []ForecastPoint      `json:"forecast"`
	AutoComment   string               `json:"auto_comment"`
}

type ModuleContribution struct {
	ModuleID            string  `json:"module_id"`
	ModuleName          string  `json:"module_name"`
	ContributionValue   float64 `json:"contribution_value"`
	ContributionPercent float64 `json:"contribution_percent"`
}

type ShapValue struct {
	FeatureName string  `json:"feature_name"`
	ModuleID    string  `json:"module_id"`
	Value       float64 `json:"value"`
	AbsValue    float64 `json:"abs_value"`
}

type ActiveFlag struct {
	FlagName    string  `json:"flag_name"`
	ModuleID    string  `json:"module_id"`
	Description string  `json:"description"`
	Severity    float64 `json:"severity"`
}

type ForecastPoint struct {
	Horizon    string  `json:"horizon"`
	TargetDate string  `json:"target_date"`
	LSI        float64 `json:"lsi"`
	Status     string  `json:"status"`
	Confidence float64 `json:"confidence"`
}
