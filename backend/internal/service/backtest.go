package service

import (
	"context"

	"github.com/ru-liquidity-sentinel/backend/internal/dto"
	"github.com/ru-liquidity-sentinel/backend/internal/grpcclient"
)

type BacktestService struct {
	client *grpcclient.LiquidityClient
}

func NewBacktestService(client *grpcclient.LiquidityClient) *BacktestService {
	return &BacktestService{
		client: client,
	}
}

func (s *BacktestService) GetBacktest(ctx context.Context, req dto.BacktestRequest) (*dto.BacktestResponse, error) {
	resp, err := s.client.GetBacktest(ctx, req)
	if err != nil {
		return nil, err
	}
	return resp, nil
}
