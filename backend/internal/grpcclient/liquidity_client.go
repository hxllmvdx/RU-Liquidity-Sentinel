package grpcclient

import (
	"context"
	"fmt"
	"time"

	pb "github.com/ru-liquidity-sentinel/backend/gen/go/liquidity/v1"
)

const (
	defaultTimeout  = 10 * time.Second
	longJobTimeout  = 60 * time.Second
	backtestTimeout = 45 * time.Second
)

func (c *LiquidityClient) GetCurrentLSI(ctx context.Context, includeShap, includeForecast, includeComment bool) (*DashboardResponse, error) {
	callCtx, cancel := context.WithTimeout(ctx, defaultTimeout)
	defer cancel()

	resp, err := c.client.GetCurrentLSI(callCtx, &pb.GetCurrentLSIRequest{
		IncludeShap:     includeShap,
		IncludeForecast: includeForecast,
		IncludeComment:  includeComment,
	})
	if err != nil {
		return nil, fmt.Errorf("grpc GetCurrentLSI failed: %w", err)
	}

	return mapLSIResponse(resp), nil
}

func (c *LiquidityClient) GetLSIHistory(ctx context.Context, from, to string, limit, offset int) (*LSIHistoryResponse, error) {
	callCtx, cancel := context.WithTimeout(ctx, defaultTimeout)
	defer cancel()

	resp, err := c.client.GetLSIHistory(callCtx, &pb.GetLSIHistoryRequest{
		Range: &pb.DateRange{
			From: from,
			To:   to,
		},
		Pagination: &pb.Pagination{
			Limit:  int32(limit),
			Offset: int32(offset),
		},
	})
	if err != nil {
		return nil, fmt.Errorf("grpc GetLSIHistory failed: %w", err)
	}

	return mapLSIHistoryResponse(resp), nil
}

func (c *LiquidityClient) RecalculateLSI(ctx context.Context, req RecalculateRequest) (*RecalculateResponse, error) {
	callCtx, cancel := context.WithTimeout(ctx, longJobTimeout)
	defer cancel()

	resp, err := c.client.RecalculateLSI(callCtx, &pb.RecalculateLSIRequest{
		Date:               req.Date,
		ForceReloadSources: req.ForceReloadSources,
		RecalculateShap:    req.RecalculateShap,
		RegenerateComment:  req.RegenerateComment,
	})
	if err != nil {
		return nil, fmt.Errorf("grpc RecalculateLSI failed: %w", err)
	}

	return mapRecalculateResponse(resp), nil
}

func (c *LiquidityClient) GetModuleSignals(ctx context.Context, moduleID, from, to string) (*ModuleSignalsResponse, error) {
	callCtx, cancel := context.WithTimeout(ctx, defaultTimeout)
	defer cancel()

	parsedModuleID, ok := parseModuleID(moduleID)
	if !ok {
		return nil, fmt.Errorf("invalid module_id: %s", moduleID)
	}

	resp, err := c.client.GetModuleSignals(callCtx, &pb.GetModuleSignalsRequest{
		ModuleId: parsedModuleID,
		Range: &pb.DateRange{
			From: from,
			To:   to,
		},
	})
	if err != nil {
		return nil, fmt.Errorf("grpc GetModuleSignals failed: %w", err)
	}

	return mapModuleSignalsResponse(resp), nil
}

func (c *LiquidityClient) GetAllModulesSnapshot(ctx context.Context, date string) (*ModulesSnapshotResponse, error) {
	callCtx, cancel := context.WithTimeout(ctx, defaultTimeout)
	defer cancel()

	resp, err := c.client.GetAllModulesSnapshot(callCtx, &pb.GetAllModulesSnapshotRequest{
		Date: date,
	})
	if err != nil {
		return nil, fmt.Errorf("grpc GetAllModulesSnapshot failed: %w", err)
	}

	return mapModulesSnapshotResponse(resp), nil
}

func (c *LiquidityClient) RunScenario(ctx context.Context, req ScenarioRequest) (*ScenarioResponse, error) {
	callCtx, cancel := context.WithTimeout(ctx, defaultTimeout)
	defer cancel()

	shocks := make([]*pb.ScenarioShock, 0, len(req.Shocks))
	for _, shock := range req.Shocks {
		parsedModuleID, ok := parseModuleID(shock.ModuleID)
		if !ok {
			return nil, fmt.Errorf("invalid module_id: %s", shock.ModuleID)
		}
		shocks = append(shocks, &pb.ScenarioShock{
			FeatureName:   shock.FeatureName,
			ModuleId:      parsedModuleID,
			Delta:         shock.Delta,
			AbsoluteValue: shock.AbsoluteValue,
			Unit:          shock.Unit,
		})
	}

	resp, err := c.client.RunScenario(callCtx, &pb.RunScenarioRequest{
		BaseDate:       req.BaseDate,
		Shocks:         shocks,
		TaxWeekEnabled: req.TaxWeekEnabled,
	})
	if err != nil {
		return nil, fmt.Errorf("grpc RunScenario failed: %w", err)
	}

	return mapScenarioResponse(resp), nil
}

func (c *LiquidityClient) GetBacktest(ctx context.Context, req BacktestRequest) (*BacktestResponse, error) {
	callCtx, cancel := context.WithTimeout(ctx, backtestTimeout)
	defer cancel()

	episode, ok := parseEpisode(req.Episode)
	if !ok {
		return nil, fmt.Errorf("invalid episode: %s", req.Episode)
	}

	pbReq := &pb.GetBacktestRequest{
		Episode:                episode,
		IncludeShap:            req.IncludeShap,
		IncludeModuleBreakdown: req.IncludeModuleBreakdown,
	}
	if req.From != "" || req.To != "" {
		pbReq.CustomRange = &pb.DateRange{
			From: req.From,
			To:   req.To,
		}
	}

	resp, err := c.client.GetBacktest(callCtx, pbReq)
	if err != nil {
		return nil, fmt.Errorf("grpc GetBacktest failed: %w", err)
	}

	return mapBacktestResponse(resp), nil
}

func (c *LiquidityClient) GenerateAutoComment(ctx context.Context, req GenerateAutoCommentRequest) (*AutoCommentResponse, error) {
	callCtx, cancel := context.WithTimeout(ctx, defaultTimeout)
	defer cancel()

	status, ok := parseStatus(req.Status)
	if !ok {
		return nil, fmt.Errorf("invalid status: %s", req.Status)
	}

	contributions := make([]*pb.NamedValue, 0, len(req.ModuleContributions))
	for _, item := range req.ModuleContributions {
		contributions = append(contributions, &pb.NamedValue{
			Name:  item.Name,
			Value: item.Value,
		})
	}

	resp, err := c.client.GenerateAutoComment(callCtx, &pb.GenerateAutoCommentRequest{
		Date:                req.Date,
		Lsi:                 req.LSI,
		Status:              status,
		ModuleContributions: contributions,
		ActiveFlags:         req.ActiveFlags,
		UpcomingEvents:      req.UpcomingEvents,
	})
	if err != nil {
		return nil, fmt.Errorf("grpc GenerateAutoComment failed: %w", err)
	}

	return mapAutoCommentResponse(resp), nil
}

func (c *LiquidityClient) ChatAnalyst(ctx context.Context, req ChatRequest) (*ChatResponse, error) {
	callCtx, cancel := context.WithTimeout(ctx, defaultTimeout)
	defer cancel()

	pbReq := &pb.ChatRequest{
		SessionId:   req.SessionID,
		UserMessage: req.UserMessage,
	}
	if req.PreferredRange != nil {
		pbReq.PreferredRange = &pb.DateRange{
			From: req.PreferredRange.From,
			To:   req.PreferredRange.To,
		}
	}

	resp, err := c.client.ChatAnalyst(callCtx, pbReq)
	if err != nil {
		return nil, fmt.Errorf("grpc ChatAnalyst failed: %w", err)
	}

	return mapChatResponse(resp), nil
}
