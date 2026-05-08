package handlers

import (
	"encoding/json"
	"net/http"
)

func RunScenario(w http.ResponseWriter, _ *http.Request) {
	_ = json.NewEncoder(w).Encode(map[string]any{
		"scenario_lsi": 55.0,
		"status":       "yellow",
	})
}
