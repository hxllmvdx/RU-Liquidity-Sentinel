package scheduler

import (
	"fmt"
	"strings"
	"time"

	"github.com/ru-liquidity-sentinel/backend/internal/config"
)

type Config struct {
	Enabled             bool
	Cron                string
	RunOnStartup        bool
	Timezone            *time.Location
	TimezoneName        string
	RecalculateDateMode string
	Timeout             time.Duration
}

func NewConfig(cfg config.SchedulerConfig) (Config, error) {
	location, err := time.LoadLocation(cfg.Timezone)
	if err != nil {
		return Config{}, fmt.Errorf("load scheduler timezone: %w", err)
	}

	mode := strings.ToLower(strings.TrimSpace(cfg.RecalculateDateMode))
	switch mode {
	case "", "today":
		mode = "today"
	case "yesterday":
	default:
		return Config{}, fmt.Errorf("unsupported scheduler recalculate date mode: %s", cfg.RecalculateDateMode)
	}

	if cfg.Timeout <= 0 {
		return Config{}, fmt.Errorf("scheduler timeout must be > 0")
	}

	return Config{
		Enabled:             cfg.Enabled,
		Cron:                cfg.Cron,
		RunOnStartup:        cfg.RunOnStartup,
		Timezone:            location,
		TimezoneName:        cfg.Timezone,
		RecalculateDateMode: mode,
		Timeout:             cfg.Timeout,
	}, nil
}
