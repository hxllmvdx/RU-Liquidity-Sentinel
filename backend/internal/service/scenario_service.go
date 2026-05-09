package service

import (
	"context"

	"github.com/ru-liquidity-sentinel/backend/internal/dto"
	"github.com/ru-liquidity-sentinel/backend/internal/grpcclient"
)

type ScenarioService struct {
	client *grpcclient.LiquidityClient
}

func NewScenarioService(client *grpcclient.LiquidityClient) *ScenarioService {
	return &ScenarioService{
		client: client,
	}
}

func (s *ScenarioService) RunScenario(ctx context.Context, req dto.ScenarioRequest) (*dto.ScenarioResponse, error) {
	res, err := s.client.RunScenario(ctx, req)
	if err != nil {
		return nil, err
	}
	return res, nil
}
