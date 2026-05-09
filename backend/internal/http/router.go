package http

import (
	"time"

	"github.com/gin-gonic/gin"
	"github.com/ru-liquidity-sentinel/backend/internal/http/handlers"
	"github.com/ru-liquidity-sentinel/backend/internal/middleware"
	"github.com/ru-liquidity-sentinel/backend/internal/service"
)

func NewRouter(services *service.Services) *gin.Engine {
	r := gin.Default()

	r.Use(
		middleware.RequestID(),
		middleware.Logging(),
		middleware.Recovery(),
		middleware.CORS("http://localhost:3000"),
		middleware.TimeoutWithOverrides(5*time.Second, map[string]time.Duration{
			"/api/recalculate": 65 * time.Second,
		}),
	)

	healthHandler := handlers.NewHealthHandler()
	dashboardHandler := handlers.NewDashboardHandler(services.Dashboard)
	lsiHandler := handlers.NewLSIHandler(services.LSI)
	modulesHandler := handlers.NewModulesHandler(services.Modules)
	scenarioHandler := handlers.NewScenarioHandler(services.Scenario)
	backtestHandler := handlers.NewBacktestHandler(services.Backtest)
	analystHandler := handlers.NewAnalystHandler(services.Analyst)

	api := r.Group("/api")
	api.GET("/health", healthHandler.Health)
	api.GET("/dashboard/current", dashboardHandler.GetCurrentDashboard)
	api.GET("/lsi/history", lsiHandler.GetHistory)
	api.POST("/recalculate", lsiHandler.Recalculate)
	api.GET("/modules", modulesHandler.ListModules)
	api.GET("/modules/snapshot", modulesHandler.GetSnapshot)
	api.GET("/modules/:id/signals", modulesHandler.GetSignals)
	api.POST("/scenario/simulate", scenarioHandler.RunScenario)
	api.GET("/backtest", backtestHandler.GetBacktest)
	api.POST("/analyst/comment", analystHandler.GenerateComment)
	api.POST("/analyst/chat", analystHandler.Chat)

	return r
}
