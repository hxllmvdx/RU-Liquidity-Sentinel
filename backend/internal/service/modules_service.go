package service

import (
	"context"

	"github.com/ru-liquidity-sentinel/backend/internal/dto"
	"github.com/ru-liquidity-sentinel/backend/internal/grpcclient"
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
}

func NewModulesService(client *grpcclient.LiquidityClient) *ModulesService {
	return &ModulesService{
		client: client,
	}
}

func (s *ModulesService) ListModules(ctx context.Context) (dto.ModulesListResponse, error) {
	return dto.ModulesListResponse{Modules: staticModules}, nil
}

func (s *ModulesService) GetSignals(ctx context.Context, moduleID, from, to string) (*dto.ModuleSignalsResponse, error) {
	resp, err := s.client.GetModuleSignals(ctx, moduleID, from, to)
	if err != nil {
		return nil, err
	}
	return &dto.ModuleSignalsResponse{
		ModuleID:    moduleID,
		Signals:     resp.Signals,
		ActiveFlags: resp.ActiveFlags,
	}, nil
}

func (s *ModulesService) GetSnapshot(ctx context.Context, date string) (*dto.ModulesSnapshotResponse, error) {
	resp, err := s.client.GetAllModulesSnapshot(ctx, date)
	if err != nil {
		return nil, err
	}
	return resp, nil
}
