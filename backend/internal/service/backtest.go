package service

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"time"

	rediscache "github.com/ru-liquidity-sentinel/backend/internal/cache/redis"
	"github.com/ru-liquidity-sentinel/backend/internal/domain"
	"github.com/ru-liquidity-sentinel/backend/internal/dto"
	"github.com/ru-liquidity-sentinel/backend/internal/grpcclient"
	"github.com/ru-liquidity-sentinel/backend/internal/mapper"
	"github.com/ru-liquidity-sentinel/backend/internal/repository/postgres"
)

type BacktestService struct {
	client *grpcclient.LiquidityClient
	repo   *postgres.BacktestRepository
	cache  *rediscache.Cache
}

func NewBacktestService(client *grpcclient.LiquidityClient, repo *postgres.BacktestRepository, cache *rediscache.Cache) *BacktestService {
	return &BacktestService{
		client: client,
		repo:   repo,
		cache:  cache,
	}
}

func (s *BacktestService) GetBacktest(ctx context.Context, req dto.BacktestRequest) (*dto.BacktestResponse, error) {
	from, to := resolveBacktestRange(req)
	if cached, err := s.cache.GetBacktest(ctx, req, from, to); err == nil && cached != nil {
		return cached, nil
	}

	fromTime, err := time.Parse(dateLayout, from)
	if err != nil {
		return nil, fmt.Errorf("parse from date: %w", err)
	}
	toTime, err := time.Parse(dateLayout, to)
	if err != nil {
		return nil, fmt.Errorf("parse to date: %w", err)
	}

	if s.repo != nil {
		resp, err := s.repo.GetBacktestResult(ctx, req.Episode, fromTime, toTime)
		if err != nil {
			return nil, err
		}

		if resp != nil {
			mapped, mapErr := mapper.BacktestResponseFromDomain(*resp)
			if mapErr != nil {
				return nil, mapErr
			}
			if cacheErr := s.cache.SetBacktest(ctx, req, from, to, mapped); cacheErr != nil {
				log.Printf("backtest cache set error: %v", cacheErr)
			}
			return mapped, nil
		}

		backtestResp, err := s.client.GetBacktest(ctx, req)
		if err != nil {
			return nil, err
		}

		metricsJSON, err := json.Marshal(backtestResp.Metrics)
		if err != nil {
			return nil, fmt.Errorf("marshal backtest metrics: %w", err)
		}
		eventsJSON, err := json.Marshal(backtestResp.Events)
		if err != nil {
			return nil, fmt.Errorf("marshal backtest events: %w", err)
		}
		historyJSON, err := json.Marshal(backtestResp.LSIHistory)
		if err != nil {
			return nil, fmt.Errorf("marshal backtest history: %w", err)
		}
		contributionsJSON, err := json.Marshal(backtestResp.AverageContributions)
		if err != nil {
			return nil, fmt.Errorf("marshal backtest contributions: %w", err)
		}

		backtestRes := domain.BacktestResult{
			Episode:              req.Episode,
			RangeFrom:            fromTime,
			RangeTo:              toTime,
			Conclusion:           &backtestResp.Conclusion,
			Metrics:              metricsJSON,
			Events:               eventsJSON,
			LSIHistory:           historyJSON,
			AverageContributions: contributionsJSON,
		}

		err = s.repo.SaveBacktestResult(ctx, backtestRes)
		if err != nil {
			return nil, err
		}

		if cacheErr := s.cache.SetBacktest(ctx, req, from, to, backtestResp); cacheErr != nil {
			log.Printf("backtest cache set error: %v", cacheErr)
		}
		return backtestResp, nil
	}

	resp, err := s.client.GetBacktest(ctx, req)
	if err != nil {
		return nil, err
	}
	if cacheErr := s.cache.SetBacktest(ctx, req, from, to, resp); cacheErr != nil {
		log.Printf("backtest cache set error: %v", cacheErr)
	}
	return resp, nil
}

func resolveBacktestRange(req dto.BacktestRequest) (string, string) {
	if strings.TrimSpace(req.From) != "" && strings.TrimSpace(req.To) != "" {
		return req.From, req.To
	}

	switch req.Episode {
	case "december_2014":
		return "2014-12-01", "2014-12-31"
	case "february_march_2022":
		return "2022-02-01", "2022-03-31"
	case "august_2023":
		return "2023-08-01", "2023-08-31"
	default:
		return req.From, req.To
	}
}
