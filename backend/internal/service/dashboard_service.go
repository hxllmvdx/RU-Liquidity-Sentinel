package service

import (
	"context"
	"log"

	rediscache "github.com/ru-liquidity-sentinel/backend/internal/cache/redis"
	"github.com/ru-liquidity-sentinel/backend/internal/domain"
	"github.com/ru-liquidity-sentinel/backend/internal/dto"
	"github.com/ru-liquidity-sentinel/backend/internal/grpcclient"
	"github.com/ru-liquidity-sentinel/backend/internal/mapper"
	"github.com/ru-liquidity-sentinel/backend/internal/repository/postgres"
)

type DashboardService struct {
	client    *grpcclient.LiquidityClient
	lsiRepo   *postgres.LSIRepository
	contrRepo *postgres.ContributionsRepository
	modRepo   *postgres.ModulesRepository
	cache     *rediscache.Cache
}

func NewDashboardService(client *grpcclient.LiquidityClient, lsiRepo *postgres.LSIRepository, contrRepo *postgres.ContributionsRepository, modRepo *postgres.ModulesRepository, cache *rediscache.Cache) *DashboardService {
	return &DashboardService{
		client:    client,
		lsiRepo:   lsiRepo,
		contrRepo: contrRepo,
		modRepo:   modRepo,
		cache:     cache,
	}
}

func (s *DashboardService) GetCurrentDashboard(ctx context.Context, includeShap, includeForecast, includeComment bool) (*dto.DashboardResponse, error) {
	if cached, err := s.cache.GetDashboard(ctx, includeShap, includeForecast, includeComment); err == nil && cached != nil {
		return cached, nil
	}

	if s.lsiRepo == nil || s.contrRepo == nil || s.modRepo == nil {
		resp, err := s.client.GetCurrentLSI(ctx, includeShap, includeForecast, includeComment)
		if err == nil && resp != nil {
			if cacheErr := s.cache.SetDashboard(ctx, includeShap, includeForecast, includeComment, resp); cacheErr != nil {
				log.Printf("dashboard cache set error: %v", cacheErr)
			}
		}
		return resp, err
	}

	latestLSI, err := s.cache.GetLatestLSI(ctx)
	if err != nil {
		log.Printf("latest lsi cache get error: %v", err)
	}
	if latestLSI == nil {
		latestLSI, err = s.lsiRepo.GetLatestLSI(ctx)
		if err != nil {
			return nil, err
		}
		if latestLSI != nil {
			if cacheErr := s.cache.SetLatestLSI(ctx, latestLSI); cacheErr != nil {
				log.Printf("latest lsi cache set error: %v", cacheErr)
			}
		}
	}
	if latestLSI == nil {
		resp, err := s.client.GetCurrentLSI(ctx, includeShap, includeForecast, includeComment)
		if err == nil && resp != nil {
			if cacheErr := s.cache.SetDashboard(ctx, includeShap, includeForecast, includeComment, resp); cacheErr != nil {
				log.Printf("dashboard cache set error: %v", cacheErr)
			}
		}
		return resp, err
	}

	contribs, err := s.contrRepo.GetContributionsByLSI(ctx, latestLSI.ID)
	if err != nil {
		return nil, err
	}

	shapValues := []domain.ShapValue{}
	if includeShap {
		shapValues, err = s.contrRepo.GetShapValuesByLSI(ctx, latestLSI.ID)
		if err != nil {
			return nil, err
		}
	}

	flags, err := s.modRepo.GetActiveFlagsForDate(ctx, latestLSI.CalculationDate, latestLSI.CalculationDate)
	if err != nil {
		return nil, err
	}

	forecast := []dto.ForecastPoint{}
	if includeForecast && s.client != nil {
		resp, err := s.client.GetCurrentLSI(ctx, false, true, false)
		if err == nil && resp != nil {
			forecast = resp.Forecast
		}
	}

	resp := mapper.DashboardResponseFromDomain(*latestLSI, contribs, shapValues, flags, forecast)
	if !includeComment {
		resp.AutoComment = ""
	}
	if !includeShap {
		resp.ShapValues = nil
	}
	if cacheErr := s.cache.SetDashboard(ctx, includeShap, includeForecast, includeComment, resp); cacheErr != nil {
		log.Printf("dashboard cache set error: %v", cacheErr)
	}
	return resp, nil
}
