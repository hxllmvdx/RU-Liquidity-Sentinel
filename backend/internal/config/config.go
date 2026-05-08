package config

import "os"

type Config struct {
	BackendPort string
	MLGRPCPort  string
}

func Load() Config {
	return Config{
		BackendPort: getEnv("BACKEND_PORT", "8080"),
		MLGRPCPort:  getEnv("ML_GRPC_PORT", "50051"),
	}
}

func getEnv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}
