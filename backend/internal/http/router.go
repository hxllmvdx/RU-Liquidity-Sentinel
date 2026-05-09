package http

import (
	"time"

	"github.com/gin-gonic/gin"
	rediscache "github.com/ru-liquidity-sentinel/backend/internal/cache/redis"
	"github.com/ru-liquidity-sentinel/backend/internal/grpcclient"
	"github.com/ru-liquidity-sentinel/backend/internal/http/handlers"
	"github.com/ru-liquidity-sentinel/backend/internal/middleware"
	"github.com/ru-liquidity-sentinel/backend/internal/repository/postgres"
	"github.com/ru-liquidity-sentinel/backend/internal/service"
)

func NewRouter(liquidityClient *grpcclient.LiquidityClient, db *postgres.DB, cache *rediscache.Cache) *gin.Engine {
	r := gin.Default()

	r.Use(
		middleware.RequestID(),
		middleware.Logging(),
		middleware.Recovery(),
		middleware.CORS("http://localhost:3000"),
		middleware.Timeout(5*time.Second),
	)

	var (
		lsiRepo      *postgres.LSIRepository
		modulesRepo  *postgres.ModulesRepository
		contrRepo    *postgres.ContributionsRepository
		backtestRepo *postgres.BacktestRepository
		chatRepo     *postgres.ChatRepository
		ragRepo      *postgres.RAGRepository
		jobRepo      *postgres.JobRepository
	)
	if db != nil {
		lsiRepo = postgres.NewLSIRepository(db)
		modulesRepo = postgres.NewModulesRepository(db)
		contrRepo = postgres.NewContributionsRepository(db)
		backtestRepo = postgres.NewBacktestRepository(db)
		chatRepo = postgres.NewChatRepository(db)
		ragRepo = postgres.NewRAGRepository(db)
		jobRepo = postgres.NewJobRepository(db)
	}

	dashboardService := service.NewDashboardService(liquidityClient, lsiRepo, contrRepo, modulesRepo, cache)
	lsiService := service.NewLSIService(liquidityClient, lsiRepo, jobRepo, cache)
	scenarioService := service.NewScenarioService(liquidityClient)
	backtestService := service.NewBacktestService(liquidityClient, backtestRepo, cache)
	modulesService := service.NewModulesService(liquidityClient, modulesRepo, cache)
	analystService := service.NewAnalystService(liquidityClient, chatRepo, ragRepo)

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
