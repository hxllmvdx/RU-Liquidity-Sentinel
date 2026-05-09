package service

import (
	rediscache "github.com/ru-liquidity-sentinel/backend/internal/cache/redis"
	"github.com/ru-liquidity-sentinel/backend/internal/grpcclient"
	"github.com/ru-liquidity-sentinel/backend/internal/repository/postgres"
)

type Dependencies struct {
	LiquidityClient *grpcclient.LiquidityClient
	DB              *postgres.DB
	Cache           *rediscache.Cache
}

type Services struct {
	Dashboard *DashboardService
	LSI       *LSIService
	Scenario  *ScenarioService
	Backtest  *BacktestService
	Modules   *ModulesService
	Analyst   *AnalystService
}

func NewServices(deps Dependencies) *Services {
	var (
		lsiRepo        *postgres.LSIRepository
		modulesRepo    *postgres.ModulesRepository
		contrRepo      *postgres.ContributionsRepository
		backtestRepo   *postgres.BacktestRepository
		chatRepo       *postgres.ChatRepository
		ragRepo        *postgres.RAGRepository
		jobRepo        *postgres.JobRepository
		dataSourceRepo *postgres.DataSourceRepository
	)

	if deps.DB != nil {
		lsiRepo = postgres.NewLSIRepository(deps.DB)
		modulesRepo = postgres.NewModulesRepository(deps.DB)
		contrRepo = postgres.NewContributionsRepository(deps.DB)
		backtestRepo = postgres.NewBacktestRepository(deps.DB)
		chatRepo = postgres.NewChatRepository(deps.DB)
		ragRepo = postgres.NewRAGRepository(deps.DB)
		jobRepo = postgres.NewJobRepository(deps.DB)
		dataSourceRepo = postgres.NewDataSourceRepository(deps.DB)
	}

	return &Services{
		Dashboard: NewDashboardService(deps.LiquidityClient, lsiRepo, contrRepo, modulesRepo, deps.Cache),
		LSI:       NewLSIService(deps.LiquidityClient, lsiRepo, jobRepo, dataSourceRepo, deps.Cache),
		Scenario:  NewScenarioService(deps.LiquidityClient),
		Backtest:  NewBacktestService(deps.LiquidityClient, backtestRepo, deps.Cache),
		Modules:   NewModulesService(deps.LiquidityClient, modulesRepo, deps.Cache),
		Analyst:   NewAnalystService(deps.LiquidityClient, chatRepo, ragRepo),
	}
}
