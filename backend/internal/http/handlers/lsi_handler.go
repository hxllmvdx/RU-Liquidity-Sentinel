package handlers

import (
	"encoding/json"
	"net/http"
)

func GetLSI(w http.ResponseWriter, _ *http.Request) {
	_ = json.NewEncoder(w).Encode(map[string]any{
		"current": 42.0,
		"history": []map[string]any{},
	})
}
