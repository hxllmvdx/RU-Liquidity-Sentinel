package main

import (
	"context"
	"log"

	_ "github.com/jackc/pgx/v5/stdlib"
	"github.com/jmoiron/sqlx"
	rediscache "github.com/ru-liquidity-sentinel/backend/internal/cache/redis"
	"github.com/ru-liquidity-sentinel/backend/internal/config"
	"github.com/ru-liquidity-sentinel/backend/internal/grpcclient"
	backendhttp "github.com/ru-liquidity-sentinel/backend/internal/http"
	"github.com/ru-liquidity-sentinel/backend/internal/repository/postgres"
)

func main() {
	cfg, err := config.Load()
	if err != nil {
		log.Fatalf("failed to load config: %v", err)
	}

	mlAddr := cfg.MLGRPCAddr
	httpAddr := ":" + cfg.BackendPort

	liquidityClient, err := grpcclient.NewLiquidityClient(mlAddr)
	if err != nil {
		log.Fatalf("failed to create liquidity grpc client: %v", err)
	}
	defer liquidityClient.Close()

	sqlDB, err := sqlx.Connect("pgx", cfg.DB_URL)
	if err != nil {
		log.Fatalf("failed to connect to postgres: %v", err)
	}
	defer sqlDB.Close()

	cache, err := rediscache.New(context.Background(), cfg.Redis)
	if err != nil {
		log.Fatalf("failed to initialize redis: %v", err)
	}
	if cache != nil {
		defer cache.Close()
	}

	router := backendhttp.NewRouter(liquidityClient, postgres.NewDB(sqlDB), cache)

	log.Printf("backend started on %s", httpAddr)
	if err := router.Run(httpAddr); err != nil {
		log.Fatalf("backend failed: %v", err)
	}
}
