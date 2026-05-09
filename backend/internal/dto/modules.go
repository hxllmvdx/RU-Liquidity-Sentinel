package dto

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
