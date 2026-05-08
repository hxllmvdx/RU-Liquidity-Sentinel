package httpserver

import (
	"encoding/json"
	"net/http"

	"github.com/ru-liquidity-sentinel/backend/internal/http/handlers"
)

func NewRouter() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) {
		_ = json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	})
	mux.HandleFunc("/api/dashboard", handlers.GetDashboard)
	mux.HandleFunc("/api/modules", handlers.GetModules)
	mux.HandleFunc("/api/lsi", handlers.GetLSI)
	mux.HandleFunc("/api/scenario", handlers.RunScenario)
	mux.HandleFunc("/api/backtest", handlers.GetBacktest)
	mux.HandleFunc("/api/analyst/chat", handlers.ChatAnalyst)
	return mux
}
