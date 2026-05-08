package handlers

import (
	"encoding/json"
	"net/http"
)

func GetBacktest(w http.ResponseWriter, _ *http.Request) {
	_ = json.NewEncoder(w).Encode(map[string]any{
		"results": []map[string]any{},
	})
}
