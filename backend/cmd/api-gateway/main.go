package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib"
	"github.com/jmoiron/sqlx"
	rediscache "github.com/ru-liquidity-sentinel/backend/internal/cache/redis"
	"github.com/ru-liquidity-sentinel/backend/internal/config"
	"github.com/ru-liquidity-sentinel/backend/internal/grpcclient"
	backendhttp "github.com/ru-liquidity-sentinel/backend/internal/http"
	"github.com/ru-liquidity-sentinel/backend/internal/repository/postgres"
	"github.com/ru-liquidity-sentinel/backend/internal/scheduler"
	"github.com/ru-liquidity-sentinel/backend/internal/service"
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

	sqlDB, err := sqlx.Connect("pgx", cfg.DB_URL)
	if err != nil {
		log.Fatalf("failed to connect to postgres: %v", err)
	}

	cache, err := rediscache.New(context.Background(), cfg.Redis)
	if err != nil {
		log.Fatalf("failed to initialize redis: %v", err)
	}

	services := service.NewServices(service.Dependencies{
		LiquidityClient: liquidityClient,
		DB:              postgres.NewDB(sqlDB),
		Cache:           cache,
	})
	router := backendhttp.NewRouter(services)

	var appScheduler *scheduler.Scheduler
	if cfg.Scheduler.Enabled {
		schedulerCfg, err := scheduler.NewConfig(cfg.Scheduler)
		if err != nil {
			log.Fatalf("failed to initialize scheduler config: %v", err)
		}
		appScheduler, err = scheduler.New(schedulerCfg, scheduler.NewRecalculationJob(services.LSI, schedulerCfg))
		if err != nil {
			log.Fatalf("failed to initialize scheduler: %v", err)
		}
	} else {
		log.Printf("scheduler disabled")
	}

	server := &http.Server{
		Addr:    httpAddr,
		Handler: router,
	}

	rootCtx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	if appScheduler != nil {
		appScheduler.Start(rootCtx)
	}

	serverErr := make(chan error, 1)
	go func() {
		log.Printf("backend started on %s", httpAddr)
		serverErr <- server.ListenAndServe()
	}()

	select {
	case err := <-serverErr:
		if err != nil && err != http.ErrServerClosed {
			log.Fatalf("backend failed: %v", err)
		}
	case <-rootCtx.Done():
		log.Printf("shutdown signal received")
	}

	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	if err := server.Shutdown(shutdownCtx); err != nil {
		log.Printf("http shutdown error: %v", err)
	}

	if appScheduler != nil {
		cronCtx := appScheduler.Stop()
		select {
		case <-cronCtx.Done():
		case <-shutdownCtx.Done():
			log.Printf("scheduler stop timeout: %v", shutdownCtx.Err())
		}
	}

	if cache != nil {
		if err := cache.Close(); err != nil {
			log.Printf("redis close error: %v", err)
		}
	}
	if err := sqlDB.Close(); err != nil {
		log.Printf("postgres close error: %v", err)
	}
	if err := liquidityClient.Close(); err != nil {
		log.Printf("grpc client close error: %v", err)
	}
}
