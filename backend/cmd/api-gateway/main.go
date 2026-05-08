package main

import (
	"log"
	"os"

	backendhttp "github.com/ru-liquidity-sentinel/backend/internal/http"

	"github.com/ru-liquidity-sentinel/backend/internal/grpcclient"
)

func main() {
	mlAddr := getEnv("ML_GRPC_ADDR", "localhost:50051")
	httpAddr := getEnv("BACKEND_HTTP_ADDR", ":8080")

	liquidityClient, err := grpcclient.NewLiquidityClient(mlAddr)
	if err != nil {
		log.Fatalf("failed to create liquidity grpc client: %v", err)
	}
	defer liquidityClient.Close()

	router := backendhttp.NewRouter(liquidityClient)

	log.Printf("backend started on %s", httpAddr)
	if err := router.Run(httpAddr); err != nil {
		log.Fatalf("backend failed: %v", err)
	}
}

func getEnv(key string, fallback string) string {
	value := os.Getenv(key)
	if value == "" {
		return fallback
	}
	return value
}
