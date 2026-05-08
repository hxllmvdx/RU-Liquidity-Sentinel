package http

import (
	nethttp "net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/ru-liquidity-sentinel/backend/internal/grpcclient"
	"github.com/ru-liquidity-sentinel/backend/internal/http/handlers"
	"github.com/ru-liquidity-sentinel/backend/internal/service"
)

func NewRouter(liquidityClient *grpcclient.LiquidityClient) *gin.Engine {
	r := gin.Default()
	r.Use(corsMiddleware())

	dashboardService := service.NewDashboardService(liquidityClient)
	lsiService := service.NewLSIService(liquidityClient)
	scenarioService := service.NewScenarioService(liquidityClient)
	backtestService := service.NewBacktestService(liquidityClient)
	modulesService := service.NewModulesService(liquidityClient)
	analystService := service.NewAnalystService(liquidityClient)

	healthHandler := handlers.NewHealthHandler()
	dashboardHandler := handlers.NewDashboardHandler(dashboardService)
	lsiHandler := handlers.NewLSIHandler(lsiService)
	modulesHandler := handlers.NewModulesHandler(modulesService)
	scenarioHandler := handlers.NewScenarioHandler(scenarioService)
	backtestHandler := handlers.NewBacktestHandler(backtestService)
	analystHandler := handlers.NewAnalystHandler(analystService)

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

func corsMiddleware() gin.HandlerFunc {
	allowedOrigin := "http://localhost:3000"
	allowedMethods := "GET, POST, OPTIONS"
	allowedHeaders := "Content-Type, Authorization"

	return func(c *gin.Context) {
		origin := c.GetHeader("Origin")
		if origin == allowedOrigin {
			c.Header("Access-Control-Allow-Origin", allowedOrigin)
			c.Header("Vary", "Origin")
		}
		c.Header("Access-Control-Allow-Methods", allowedMethods)
		c.Header("Access-Control-Allow-Headers", allowedHeaders)

		if c.Request.Method == nethttp.MethodOptions {
			if origin != "" && origin != allowedOrigin {
				c.AbortWithStatus(nethttp.StatusForbidden)
				return
			}
			if !strings.Contains(allowedMethods, c.GetHeader("Access-Control-Request-Method")) && c.GetHeader("Access-Control-Request-Method") != "" {
				c.AbortWithStatus(nethttp.StatusMethodNotAllowed)
				return
			}
			c.AbortWithStatus(nethttp.StatusNoContent)
			return
		}

		c.Next()
	}
}
