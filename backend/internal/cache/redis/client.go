package redis

import (
	"context"
	"fmt"
	"log"
	"time"

	goredis "github.com/redis/go-redis/v9"
	"github.com/ru-liquidity-sentinel/backend/internal/config"
)

type Cache struct {
	client *goredis.Client
	cfg    config.RedisConfig
}

func New(ctx context.Context, cfg config.RedisConfig) (*Cache, error) {
	if !cfg.Enabled {
		return nil, nil
	}

	client := goredis.NewClient(&goredis.Options{
		Addr:     cfg.Addr,
		Password: cfg.Password,
		DB:       cfg.DB,
	})

	pingCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	if err := client.Ping(pingCtx).Err(); err != nil {
		_ = client.Close()
		return nil, fmt.Errorf("ping redis: %w", err)
	}

	log.Printf("redis client connected addr=%s db=%d", cfg.Addr, cfg.DB)
	return &Cache{
		client: client,
		cfg:    cfg,
	}, nil
}

func (c *Cache) Close() error {
	if c == nil || c.client == nil {
		return nil
	}

	return c.client.Close()
}

func (c *Cache) Enabled() bool {
	return c != nil && c.client != nil
}
