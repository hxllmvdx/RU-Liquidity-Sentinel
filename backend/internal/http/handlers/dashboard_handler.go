package handlers

import (
	"encoding/json"
	"net/http"
)

func GetDashboard(w http.ResponseWriter, _ *http.Request) {
	_ = json.NewEncoder(w).Encode(map[string]any{
		"lsi":    42.0,
		"status": "yellow",
	})
}
