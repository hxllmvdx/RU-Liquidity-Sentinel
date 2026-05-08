package handlers

import (
	"encoding/json"
	"net/http"
)

func ChatAnalyst(w http.ResponseWriter, _ *http.Request) {
	_ = json.NewEncoder(w).Encode(map[string]any{
		"answer": "Analyst stub response",
	})
}
