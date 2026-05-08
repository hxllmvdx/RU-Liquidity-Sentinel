package main

import (
	"log"
	"net/http"
	"os"

	httpserver "github.com/ru-liquidity-sentinel/backend/internal/http"
)

func main() {
	port := os.Getenv("BACKEND_PORT")
	if port == "" {
		port = "8080"
	}

	router := httpserver.NewRouter()
	log.Printf("api-gateway listening on :%s", port)
	if err := http.ListenAndServe(":"+port, router); err != nil {
		log.Fatal(err)
	}
}
