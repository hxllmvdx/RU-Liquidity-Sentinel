package config

import "os"

type Config struct {
	BackendPort string
	MLGRPCPort  string
	DB_URL      string
}

func Load() Config {
	return Config{
		BackendPort: getEnv("BACKEND_PORT", "8080"),
		MLGRPCPort:  getEnv("ML_GRPC_PORT", "50051"),
		DB_URL:      getEnv("DATABASE_URL", "postgres://ru_liquidity_user:password@localhost:5432/ru_liquidity_sentinel?sslmode=disable"),
	}
}

func getEnv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}
