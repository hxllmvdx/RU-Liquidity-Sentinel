package service

import (
	"context"

	"github.com/ru-liquidity-sentinel/backend/internal/dto"
	"github.com/ru-liquidity-sentinel/backend/internal/grpcclient"
)

type AnalystService struct {
	client *grpcclient.LiquidityClient
}

func NewAnalystService(client *grpcclient.LiquidityClient) *AnalystService {
	return &AnalystService{
		client: client,
	}
}

func (s *AnalystService) GenerateComment(ctx context.Context, req dto.GenerateAutoCommentRequest) (*dto.AutoCommentResponse, error) {
	resp, err := s.client.GenerateAutoComment(ctx, req)
	if err != nil {
		return nil, err
	}
	return &dto.AutoCommentResponse{
		Comment:       resp.Comment,
		Retrospective: resp.Retrospective,
		Outlook:       resp.Outlook,
	}, nil
}

func (s *AnalystService) Chat(ctx context.Context, req dto.ChatRequest) (*dto.ChatResponse, error) {
	resp, err := s.client.ChatAnalyst(ctx, req)
	if err != nil {
		return nil, err
	}
	return &dto.ChatResponse{
		SessionID: resp.SessionID,
		Answer:    resp.Answer,
		Contexts:  resp.Contexts,
	}, nil
}
