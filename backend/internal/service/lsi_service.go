package service

import (
	"context"
	"fmt"
	"log"
	"strings"
	"sync/atomic"
	"time"

	rediscache "github.com/ru-liquidity-sentinel/backend/internal/cache/redis"
	"github.com/ru-liquidity-sentinel/backend/internal/domain"
	"github.com/ru-liquidity-sentinel/backend/internal/dto"
	"github.com/ru-liquidity-sentinel/backend/internal/grpcclient"
	"github.com/ru-liquidity-sentinel/backend/internal/mapper"
	"github.com/ru-liquidity-sentinel/backend/internal/repository/postgres"
)

type LSIService struct {
	client     *grpcclient.LiquidityClient
	lsiRepo    *postgres.LSIRepository
	jobRepo    *postgres.JobRepository
	sourceRepo *postgres.DataSourceRepository
	cache      *rediscache.Cache
	running    atomic.Bool
}

const dateLayout = "2006-01-02"

func NewLSIService(client *grpcclient.LiquidityClient, lsiRepo *postgres.LSIRepository, jobRepo *postgres.JobRepository, sourceRepo *postgres.DataSourceRepository, cache *rediscache.Cache) *LSIService {
	return &LSIService{
		client:     client,
		lsiRepo:    lsiRepo,
		jobRepo:    jobRepo,
		sourceRepo: sourceRepo,
		cache:      cache,
	}
}

func (s *LSIService) GetHistory(ctx context.Context, from, to string, limit, offset int) (*dto.LSIHistoryResponse, error) {
	fromTime, err := time.Parse(dateLayout, from)
	if err != nil {
		return nil, fmt.Errorf("parse from date: %w", err)
	}
	toTime, err := time.Parse(dateLayout, to)
	if err != nil {
		return nil, fmt.Errorf("parse to date: %w", err)
	}

	if cached, err := s.cache.GetLSIHistory(ctx, from, to, limit, offset); err == nil && cached != nil {
		return cached, nil
	}

	if s.lsiRepo == nil {
		resp, err := s.client.GetLSIHistory(ctx, from, to, limit, offset)
		if err == nil && resp != nil {
			if cacheErr := s.cache.SetLSIHistory(ctx, from, to, limit, offset, resp); cacheErr != nil {
				log.Printf("lsi history cache set error: %v", cacheErr)
			}
		}
		return resp, err
	}

	history, err := s.lsiRepo.GetLSIHistory(ctx, fromTime, toTime, limit, offset)
	if err != nil {
		return nil, err
	}

	resp := mapper.LSIHistoryResponseFromDomain(history)
	if cacheErr := s.cache.SetLSIHistory(ctx, from, to, limit, offset, resp); cacheErr != nil {
		log.Printf("lsi history cache set error: %v", cacheErr)
	}
	return resp, nil
}

func (s *LSIService) Recalculate(ctx context.Context, req dto.RecalculateRequest) (*dto.RecalculateResponse, error) {
	lockToken, releaseLocal, err := s.acquireRecalculationLock(ctx)
	if err != nil {
		if err == rediscache.ErrLockAlreadyHeld || err == ErrRecalculationInProgress {
			return nil, ErrRecalculationInProgress
		}
		return nil, err
	}
	defer releaseLocal()
	if lockToken != "" {
		defer func() {
			if releaseErr := s.cache.ReleaseRecalculationLock(ctx, lockToken); releaseErr != nil {
				log.Printf("recalculation lock release error: %v", releaseErr)
			}
		}()
	}

	var requestedDate *time.Time
	if req.Date != "" {
		parsedDate, parseErr := time.Parse(dateLayout, req.Date)
		if parseErr != nil {
			return nil, fmt.Errorf("parse requested date: %w", parseErr)
		}
		requestedDate = &parsedDate
	}

	var job *domain.RecalculationJob
	if s.jobRepo != nil {
		jobCtx, cancel := s.jobStatusContext(ctx)
		defer cancel()

		job, err = s.jobRepo.CreateJob(jobCtx, domain.RecalculationJob{
			RequestedDate:      requestedDate,
			Status:             "pending",
			ForceReloadSources: req.ForceReloadSources,
			RecalculateShap:    req.RecalculateShap,
			RegenerateComment:  req.RegenerateComment,
		})
		if err != nil {
			return nil, err
		}
		if cacheErr := s.cache.SetJobStatus(ctx, *job); cacheErr != nil {
			log.Printf("job cache set error: %v", cacheErr)
		}
		if err := s.jobRepo.MarkJobRunning(jobCtx, job.ID); err != nil {
			if failErr := s.jobRepo.MarkJobFailure(jobCtx, job.ID, err.Error()); failErr != nil {
				log.Printf("mark job failure after running transition error: %v", failErr)
			}
			return nil, err
		}
		job.Status = "running"
		if cacheErr := s.cache.SetJobStatus(ctx, *job); cacheErr != nil {
			log.Printf("job cache set error: %v", cacheErr)
		}
	}

	result, err := s.client.RecalculateLSI(ctx, req)
	if err != nil {
		if job != nil {
			jobCtx, cancel := s.jobStatusContext(ctx)
			defer cancel()
			if markErr := s.jobRepo.MarkJobFailure(jobCtx, job.ID, err.Error()); markErr != nil {
				log.Printf("mark job failure error: %v", markErr)
			}
		}
		return nil, err
	}

	if s.lsiRepo == nil || result == nil || result.Result == nil {
		return result, nil
	}

	calculationDate, err := time.Parse(dateLayout, result.Result.Date)
	if err != nil {
		return result, nil
	}

	var confidence *float64
	if result.Result.Confidence != 0 {
		confidence = &result.Result.Confidence
	}

	var autoComment *string
	if result.Result.AutoComment != "" {
		autoComment = &result.Result.AutoComment
	}

	value := domain.LSIValue{
		CalculationDate: calculationDate,
		LSI:             result.Result.LSI,
		Status:          result.Result.Status,
		Confidence:      confidence,
		AutoComment:     autoComment,
		CalculatedAt:    time.Now(),
	}

	if err := s.lsiRepo.SaveLSIValue(ctx, value); err != nil {
		if job != nil {
			jobCtx, cancel := s.jobStatusContext(ctx)
			defer cancel()
			if markErr := s.jobRepo.MarkJobFailure(jobCtx, job.ID, err.Error()); markErr != nil {
				log.Printf("mark job failure error: %v", markErr)
			}
		}
		return nil, err
	}
	log.Printf("recalculation persisted lsi calculation_date=%s", calculationDate.Format(dateLayout))

	if err := s.markUpdatedSources(ctx, result.UpdatedSources); err != nil {
		log.Printf("data sources update warning: %v", err)
	}

	latestLSI, err := s.lsiRepo.GetLatestLSI(ctx)
	if err != nil {
		return nil, err
	}

	if invalidateErr := s.invalidateAfterRecalculation(ctx); invalidateErr != nil {
		log.Printf("cache invalidation after recalculation error: %v", invalidateErr)
	}

	if latestLSI != nil {
		if cacheErr := s.cache.SetLatestLSI(ctx, latestLSI); cacheErr != nil {
			log.Printf("latest lsi cache set error: %v", cacheErr)
		}
	}

	if job != nil {
		jobCtx, cancel := s.jobStatusContext(ctx)
		defer cancel()

		if latestLSI != nil {
			if err := s.jobRepo.MarkJobSuccess(jobCtx, job.ID, &latestLSI.ID, result.UpdatedSources); err != nil {
				log.Printf("mark job success error: %v", err)
			} else {
				job.Status = "success"
				job.ResultLSIValueID = &latestLSI.ID
				if cacheErr := s.cache.SetJobStatus(jobCtx, *job); cacheErr != nil {
					log.Printf("job cache set error: %v", cacheErr)
				}
			}
		} else if err := s.jobRepo.MarkJobSuccess(jobCtx, job.ID, nil, result.UpdatedSources); err != nil {
			log.Printf("mark job success error: %v", err)
		}
	}

	return result, nil
}

func (s *LSIService) acquireRecalculationLock(ctx context.Context) (string, func(), error) {
	if !s.running.CompareAndSwap(false, true) {
		return "", func() {}, ErrRecalculationInProgress
	}

	releaseLocal := func() {
		s.running.Store(false)
	}

	lockToken, err := s.cache.AcquireRecalculationLock(ctx)
	if err != nil {
		releaseLocal()
		if err == rediscache.ErrLockAlreadyHeld {
			return "", func() {}, ErrRecalculationInProgress
		}
		return "", func() {}, err
	}

	return lockToken, releaseLocal, nil
}

func (s *LSIService) markUpdatedSources(ctx context.Context, updatedSources []string) error {
	if s.sourceRepo == nil || len(updatedSources) == 0 {
		return nil
	}

	activeSources, err := s.sourceRepo.GetActiveSources(ctx)
	if err != nil {
		return err
	}

	activeByCode := make(map[string]struct{}, len(activeSources))
	for _, source := range activeSources {
		activeByCode[strings.ToUpper(source.SourceCode)] = struct{}{}
	}

	loadedAt := time.Now()
	for _, sourceCode := range updatedSources {
		if _, ok := activeByCode[strings.ToUpper(sourceCode)]; !ok {
			continue
		}
		if err := s.sourceRepo.UpdateLoadSuccess(ctx, sourceCode, loadedAt); err != nil {
			log.Printf("data source success update warning source=%s err=%v", sourceCode, err)
		}
	}

	return nil
}

func (s *LSIService) jobStatusContext(ctx context.Context) (context.Context, context.CancelFunc) {
	return context.WithTimeout(context.WithoutCancel(ctx), 5*time.Second)
}

func (s *LSIService) invalidateAfterRecalculation(ctx context.Context) error {
	if err := s.cache.InvalidateLatestLSI(ctx); err != nil {
		return err
	}
	if err := s.cache.InvalidateDashboard(ctx); err != nil {
		return err
	}
	if err := s.cache.InvalidateModulesSnapshot(ctx); err != nil {
		return err
	}
	if err := s.cache.InvalidateModuleSignals(ctx); err != nil {
		return err
	}
	if err := s.cache.InvalidateLSIHistory(ctx); err != nil {
		return err
	}
	return nil
}
