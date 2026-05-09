package service

import (
	"context"
	"encoding/json"

	"github.com/ru-liquidity-sentinel/backend/internal/domain"
	"github.com/ru-liquidity-sentinel/backend/internal/dto"
	"github.com/ru-liquidity-sentinel/backend/internal/grpcclient"
	"github.com/ru-liquidity-sentinel/backend/internal/repository/postgres"
)

type AnalystService struct {
	client   *grpcclient.LiquidityClient
	chatRepo *postgres.ChatRepository
	ragRepo  *postgres.RAGRepository
}

func NewAnalystService(client *grpcclient.LiquidityClient, chatRepo *postgres.ChatRepository, ragRepo *postgres.RAGRepository) *AnalystService {
	return &AnalystService{
		client:   client,
		chatRepo: chatRepo,
		ragRepo:  ragRepo,
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

	contexts := resp.Contexts

	if s.chatRepo == nil {
		return &dto.ChatResponse{
			SessionID: resp.SessionID,
			Answer:    resp.Answer,
			Contexts:  contexts,
		}, nil
	}

	session, err := s.chatRepo.CreateOrGetSession(ctx, req.SessionID, nil)
	if err != nil {
		return nil, err
	}

	userMessage := domain.ChatMessage{
		SessionID: session.ID,
		Role:      "user",
		Content:   req.UserMessage,
	}
	if err := s.chatRepo.SaveMessage(ctx, userMessage); err != nil {
		return nil, err
	}

	payload, err := json.Marshal(contexts)
	if err != nil {
		return nil, err
	}

	assistantMessage := domain.ChatMessage{
		SessionID: session.ID,
		Role:      "assistant",
		Content:   resp.Answer,
		Contexts:  payload,
	}
	if err := s.chatRepo.SaveMessage(ctx, assistantMessage); err != nil {
		return nil, err
	}

	return &dto.ChatResponse{
		SessionID: resp.SessionID,
		Answer:    resp.Answer,
		Contexts:  contexts,
	}, nil
}
