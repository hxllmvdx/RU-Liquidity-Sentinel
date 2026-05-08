package service

import (
	"context"

	"github.com/ru-liquidity-sentinel/backend/internal/dto"
	"github.com/ru-liquidity-sentinel/backend/internal/grpcclient"
)

type LSIService struct {
	client *grpcclient.LiquidityClient
}

func NewLSIService(client *grpcclient.LiquidityClient) *LSIService {
	return &LSIService{
		client: client,
	}
}

func (s *LSIService) GetHistory(ctx context.Context, from, to string, limit, offset int) (*dto.LSIHistoryResponse, error) {
	history, err := s.client.GetLSIHistory(ctx, from, to, limit, offset)
	if err != nil {
		return nil, err
	}
	return history, nil
}

func (s *LSIService) Recalculate(ctx context.Context, req dto.RecalculateRequest) (*dto.RecalculateResponse, error) {
	result, err := s.client.RecalculateLSI(ctx, req)
	if err != nil {
		return nil, err
	}
	return result, nil
}
