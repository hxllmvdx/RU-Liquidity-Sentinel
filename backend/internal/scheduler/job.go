package scheduler

import (
	"context"
	"errors"
	"log"
	"time"

	"github.com/ru-liquidity-sentinel/backend/internal/dto"
	"github.com/ru-liquidity-sentinel/backend/internal/service"
)

type RecalculationRunner interface {
	Recalculate(ctx context.Context, req dto.RecalculateRequest) (*dto.RecalculateResponse, error)
}

type RecalculationJob struct {
	service RecalculationRunner
	cfg     Config
}

func NewRecalculationJob(service RecalculationRunner, cfg Config) *RecalculationJob {
	return &RecalculationJob{
		service: service,
		cfg:     cfg,
	}
}

func (j *RecalculationJob) Run(parent context.Context) {
	startedAt := time.Now()
	req := dto.RecalculateRequest{
		Date:               j.resolveRequestedDate(startedAt.In(j.cfg.Timezone)),
		ForceReloadSources: false,
		RecalculateShap:    true,
		RegenerateComment:  true,
	}

	ctx, cancel := context.WithTimeout(parent, j.cfg.Timeout)
	defer cancel()

	log.Printf("scheduler job started trigger=scheduled requested_date=%s timeout=%s", req.Date, j.cfg.Timeout)
	resp, err := j.service.Recalculate(ctx, req)
	duration := time.Since(startedAt)
	if err != nil {
		if errors.Is(err, service.ErrRecalculationInProgress) {
			log.Printf("scheduler job skipped trigger=scheduled reason=lock_busy duration=%s", duration)
			return
		}
		log.Printf("scheduler job failed trigger=scheduled requested_date=%s duration=%s err=%v", req.Date, duration, err)
		return
	}

	updatedSources := 0
	if resp != nil {
		updatedSources = len(resp.UpdatedSources)
	}
	log.Printf("scheduler job succeeded trigger=scheduled requested_date=%s duration=%s updated_sources=%d", req.Date, duration, updatedSources)
}

func (j *RecalculationJob) resolveRequestedDate(now time.Time) string {
	switch j.cfg.RecalculateDateMode {
	case "yesterday":
		return now.AddDate(0, 0, -1).Format("2006-01-02")
	default:
		return now.Format("2006-01-02")
	}
}
