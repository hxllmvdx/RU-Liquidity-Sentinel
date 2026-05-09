package config

import (
	"fmt"
	"os"
	"strconv"
	"time"
)

type Config struct {
	BackendPort string
	MLGRPCAddr  string
	DB_URL      string
	Redis       RedisConfig
}

type RedisConfig struct {
	Enabled          bool
	Addr             string
	Password         string
	DB               int
	DefaultTTL       time.Duration
	DashboardTTL     time.Duration
	LSITTL           time.Duration
	ModulesTTL       time.Duration
	JobTTL           time.Duration
	LockTTL          time.Duration
	BacktestTTL      time.Duration
	ModuleSignalsTTL time.Duration
	HistoryTTL       time.Duration
}

func Load() (Config, error) {
	cfg := Config{
		BackendPort: getEnv("BACKEND_PORT", "8080"),
		MLGRPCAddr:  getEnv("ML_GRPC_ADDR", "ml-services:50051"),
		DB_URL:      getEnv("DATABASE_URL", "postgres://ru_liquidity_user:password@localhost:5432/ru_liquidity_sentinel?sslmode=disable"),
	}

	redisEnabled, err := getEnvBool("REDIS_ENABLED", false)
	if err != nil {
		return Config{}, err
	}

	redisDB, err := getEnvInt("REDIS_DB", 0)
	if err != nil {
		return Config{}, err
	}

	defaultTTL, err := getEnvSeconds("REDIS_DEFAULT_TTL_SECONDS", 300)
	if err != nil {
		return Config{}, err
	}
	dashboardTTL, err := getEnvSeconds("REDIS_DASHBOARD_TTL_SECONDS", 90)
	if err != nil {
		return Config{}, err
	}
	lsiTTL, err := getEnvSeconds("REDIS_LSI_TTL_SECONDS", 180)
	if err != nil {
		return Config{}, err
	}
	modulesTTL, err := getEnvSeconds("REDIS_MODULES_TTL_SECONDS", 180)
	if err != nil {
		return Config{}, err
	}
	jobTTL, err := getEnvSeconds("REDIS_JOB_TTL_SECONDS", 900)
	if err != nil {
		return Config{}, err
	}
	lockTTL, err := getEnvSeconds("REDIS_LOCK_TTL_SECONDS", 900)
	if err != nil {
		return Config{}, err
	}
	backtestTTL, err := getEnvSeconds("REDIS_BACKTEST_TTL_SECONDS", 1800)
	if err != nil {
		return Config{}, err
	}
	moduleSignalsTTL, err := getEnvSeconds("REDIS_MODULE_SIGNALS_TTL_SECONDS", 600)
	if err != nil {
		return Config{}, err
	}
	historyTTL, err := getEnvSeconds("REDIS_LSI_HISTORY_TTL_SECONDS", 300)
	if err != nil {
		return Config{}, err
	}

	cfg.Redis = RedisConfig{
		Enabled:          redisEnabled,
		Addr:             getEnv("REDIS_ADDR", "localhost:6379"),
		Password:         getEnv("REDIS_PASSWORD", ""),
		DB:               redisDB,
		DefaultTTL:       defaultTTL,
		DashboardTTL:     dashboardTTL,
		LSITTL:           lsiTTL,
		ModulesTTL:       modulesTTL,
		JobTTL:           jobTTL,
		LockTTL:          lockTTL,
		BacktestTTL:      backtestTTL,
		ModuleSignalsTTL: moduleSignalsTTL,
		HistoryTTL:       historyTTL,
	}
	return cfg, nil
}

func getEnv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}

func getEnvBool(key string, fallback bool) (bool, error) {
	value := os.Getenv(key)
	if value == "" {
		return fallback, nil
	}

	parsed, err := strconv.ParseBool(value)
	if err != nil {
		return false, fmt.Errorf("parse %s: %w", key, err)
	}

	return parsed, nil
}

func getEnvInt(key string, fallback int) (int, error) {
	value := os.Getenv(key)
	if value == "" {
		return fallback, nil
	}

	parsed, err := strconv.Atoi(value)
	if err != nil {
		return 0, fmt.Errorf("parse %s: %w", key, err)
	}

	return parsed, nil
}

func getEnvSeconds(key string, fallback int) (time.Duration, error) {
	value := os.Getenv(key)
	if value == "" {
		return time.Duration(fallback) * time.Second, nil
	}

	parsed, err := strconv.Atoi(value)
	if err != nil {
		return 0, fmt.Errorf("parse %s: %w", key, err)
	}

	return time.Duration(parsed) * time.Second, nil
}
