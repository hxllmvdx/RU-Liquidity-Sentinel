package grpcclient

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

type ModuleDefinition struct {
	ModuleID    string `json:"module_id"`
	ModuleName  string `json:"module_name"`
	Description string `json:"description"`
}

type ModulesListResponse struct {
	Modules []ModuleDefinition `json:"modules"`
}

type ModuleSignal struct {
	Date       string  `json:"date"`
	ModuleID   string  `json:"module_id"`
	SignalName string  `json:"signal_name"`
	RawValue   float64 `json:"raw_value"`
	MadScore   float64 `json:"mad_score"`
	Flag       bool    `json:"flag"`
	Unit       string  `json:"unit"`
}

type ModuleSignalsResponse struct {
	ModuleID    string         `json:"module_id"`
	Signals     []ModuleSignal `json:"signals"`
	ActiveFlags []ActiveFlag   `json:"active_flags"`
}

type ModuleSnapshot struct {
	ModuleID    string         `json:"module_id"`
	ModuleName  string         `json:"module_name"`
	ModuleScore float64        `json:"module_score"`
	Signals     []ModuleSignal `json:"signals"`
	ActiveFlags []ActiveFlag   `json:"active_flags"`
}

type ModulesSnapshotResponse struct {
	Date    string           `json:"date"`
	Modules []ModuleSnapshot `json:"modules"`
}

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

type BacktestRequest struct {
	Episode                string `json:"episode"`
	From                   string `json:"from"`
	To                     string `json:"to"`
	IncludeShap            bool   `json:"include_shap"`
	IncludeModuleBreakdown bool   `json:"include_module_breakdown"`
}

type DateRange struct {
	From string `json:"from"`
	To   string `json:"to"`
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

type NamedValue struct {
	Name  string  `json:"name"`
	Value float64 `json:"value"`
}

type GenerateAutoCommentRequest struct {
	Date                string       `json:"date"`
	LSI                 float64      `json:"lsi"`
	Status              string       `json:"status"`
	ModuleContributions []NamedValue `json:"module_contributions"`
	ActiveFlags         []string     `json:"active_flags"`
	UpcomingEvents      []string     `json:"upcoming_events"`
}

type AutoCommentResponse struct {
	Comment       string `json:"comment"`
	Retrospective string `json:"retrospective"`
	Outlook       string `json:"outlook"`
}

type ChatRequest struct {
	SessionID      string     `json:"session_id"`
	UserMessage    string     `json:"user_message"`
	PreferredRange *DateRange `json:"preferred_range,omitempty"`
}

type ChatContext struct {
	SourceType string  `json:"source_type"`
	Title      string  `json:"title"`
	Content    string  `json:"content"`
	Relevance  float64 `json:"relevance"`
}

type ChatResponse struct {
	SessionID string        `json:"session_id"`
	Answer    string        `json:"answer"`
	Contexts  []ChatContext `json:"contexts"`
}
