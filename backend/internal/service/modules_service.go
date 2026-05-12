package service

import (
	"context"
	"log"
	"time"

	rediscache "github.com/ru-liquidity-sentinel/backend/internal/cache/redis"
	"github.com/ru-liquidity-sentinel/backend/internal/dto"
	"github.com/ru-liquidity-sentinel/backend/internal/grpcclient"
	"github.com/ru-liquidity-sentinel/backend/internal/mapper"
	"github.com/ru-liquidity-sentinel/backend/internal/repository/postgres"
)

var staticModules = []dto.ModuleDefinition{
	{
		ModuleID:    "M1_RESERVES",
		ModuleName:  "Усреднение обязательных резервов",
		Description: "Оценивает напряжение через спред обязательных резервов и RUONIA.",
	},
	{
		ModuleID:    "M2_REPO",
		ModuleName:  "Аукционы репо ЦБ",
		Description: "Оценивает спрос банков на ликвидность через cover ratio и ставочные спреды.",
	},
	{
		ModuleID:    "M3_OFZ",
		ModuleName:  "Размещение ОФЗ",
		Description: "Оценивает спрос на государственные облигации и признаки недоспроса.",
	},
	{
		ModuleID:    "M4_TAX",
		ModuleName:  "Налоговый период и сезонность",
		Description: "Учитывает налоговые даты, конец месяца и квартала как сезонный фактор.",
	},
	{
		ModuleID:    "M5_TREASURY",
		ModuleName:  "Средства федерального казначейства",
		Description: "Отслеживает бюджетный канал притока и оттока ликвидности.",
	},
}

type ModulesService struct {
	client *grpcclient.LiquidityClient
	repo   *postgres.ModulesRepository
	cache  *rediscache.Cache
}

func NewModulesService(client *grpcclient.LiquidityClient, repo *postgres.ModulesRepository, cache *rediscache.Cache) *ModulesService {
	return &ModulesService{
		client: client,
		repo:   repo,
		cache:  cache,
	}
}

func (s *ModulesService) ListModules(ctx context.Context) (dto.ModulesListResponse, error) {
	return dto.ModulesListResponse{Modules: staticModules}, nil
}

func (s *ModulesService) GetSignals(ctx context.Context, moduleID, from, to string) (*dto.ModuleSignalsResponse, error) {
	if cached, err := s.cache.GetModuleSignals(ctx, moduleID, from, to); err == nil && cached != nil {
		return cached, nil
	}

	fromTime, err := time.Parse(dateLayout, from)
	if err != nil {
		return nil, err
	}
	toTime, err := time.Parse(dateLayout, to)
	if err != nil {
		return nil, err
	}

	if s.repo == nil {
		resp, err := s.client.GetModuleSignals(ctx, moduleID, from, to)
		if err != nil {
			return nil, err
		}
		if cacheErr := s.cache.SetModuleSignals(ctx, moduleID, from, to, resp); cacheErr != nil {
			log.Printf("module signals cache set error: %v", cacheErr)
		}
		return resp, err
	}

	sigs, err := s.repo.GetModuleSignals(ctx, moduleID, fromTime, toTime)
	if err != nil {
		return nil, err
	}

	flags, err := s.repo.GetActiveFlags(ctx, moduleID, fromTime, toTime)
	if err != nil {
		return nil, err
	}

	resp := &dto.ModuleSignalsResponse{
		ModuleID:    moduleID,
		Signals:     mapper.ModuleSignalsFromDomain(sigs),
		ActiveFlags: mapper.ActiveFlagsFromDomain(flags),
	}
	if cacheErr := s.cache.SetModuleSignals(ctx, moduleID, from, to, resp); cacheErr != nil {
		log.Printf("module signals cache set error: %v", cacheErr)
	}
	return resp, nil
}

func (s *ModulesService) GetSnapshot(ctx context.Context, date string) (*dto.ModulesSnapshotResponse, error) {
	if cached, err := s.cache.GetModulesSnapshot(ctx, date); err == nil && cached != nil {
		return cached, nil
	}

	resp, err := s.client.GetAllModulesSnapshot(ctx, date)
	if err != nil {
		return nil, err
	}
	if cacheErr := s.cache.SetModulesSnapshot(ctx, date, resp); cacheErr != nil {
		log.Printf("modules snapshot cache set error: %v", cacheErr)
	}
	return resp, nil
}
