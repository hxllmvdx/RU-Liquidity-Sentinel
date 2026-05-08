package service

import (
	"context"

	"github.com/ru-liquidity-sentinel/backend/internal/dto"
	"github.com/ru-liquidity-sentinel/backend/internal/grpcclient"
)

type DashboardService struct {
	client *grpcclient.LiquidityClient
}

func NewDashboardService(client *grpcclient.LiquidityClient) *DashboardService {
	return &DashboardService{
		client: client,
	}
}

func (s *DashboardService) GetCurrentDashboard(ctx context.Context, includeShap, includeForecast, includeComment bool) (*dto.DashboardResponse, error) {
	resp, err := s.client.GetCurrentLSI(ctx, includeShap, includeForecast, includeComment)
	if err != nil {
		return nil, err
	}
	return resp, err
}
