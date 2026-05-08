package handlers

import (
	"encoding/json"
	"net/http"
)

func GetModules(w http.ResponseWriter, _ *http.Request) {
	_ = json.NewEncoder(w).Encode([]map[string]any{
		{"id": "m1", "name": "Reserves Averaging"},
		{"id": "m2", "name": "CBR Repo Auctions"},
	})
}
