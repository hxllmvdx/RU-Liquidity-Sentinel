package handlers

import (
	"crypto/rand"
	"encoding/hex"
	"net/http"
	"strings"

	"github.com/gin-gonic/gin"
	"github.com/ru-liquidity-sentinel/backend/internal/dto"
	"github.com/ru-liquidity-sentinel/backend/internal/service"
)

type AnalystHandler struct {
	analystService *service.AnalystService
}

func NewAnalystHandler(analystService *service.AnalystService) *AnalystHandler {
	return &AnalystHandler{analystService: analystService}
}

func (h *AnalystHandler) GenerateComment(c *gin.Context) {
	var req dto.GenerateAutoCommentRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		writeError(c, http.StatusBadRequest, "BAD_REQUEST", "invalid request body")
		return
	}
	if !validateDateString(req.Date) {
		writeError(c, http.StatusBadRequest, "BAD_REQUEST", "date is required and must be in YYYY-MM-DD format")
		return
	}
	if req.LSI < 0 || req.LSI > 100 {
		writeError(c, http.StatusBadRequest, "BAD_REQUEST", "lsi must be between 0 and 100")
		return
	}
	if req.Status != "green" && req.Status != "yellow" && req.Status != "red" {
		writeError(c, http.StatusBadRequest, "BAD_REQUEST", "status must be green, yellow, or red")
		return
	}

	resp, err := h.analystService.GenerateComment(c.Request.Context(), req)
	if err != nil {
		writeError(c, http.StatusBadGateway, "ML_SERVICE_UNAVAILABLE", "failed to call ML service")
		return
	}

	c.JSON(http.StatusOK, resp)
}

func (h *AnalystHandler) Chat(c *gin.Context) {
	var req dto.ChatRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		writeError(c, http.StatusBadRequest, "BAD_REQUEST", "invalid request body")
		return
	}
	if strings.TrimSpace(req.UserMessage) == "" {
		writeError(c, http.StatusBadRequest, "BAD_REQUEST", "user_message must not be empty")
		return
	}
	if req.PreferredRange != nil && !validateDateRange(req.PreferredRange.From, req.PreferredRange.To) {
		writeError(c, http.StatusBadRequest, "BAD_REQUEST", "preferred_range must be a valid date range")
		return
	}
	if strings.TrimSpace(req.SessionID) == "" {
		req.SessionID = newSessionID()
	}

	resp, err := h.analystService.Chat(c.Request.Context(), req)
	if err != nil {
		writeError(c, http.StatusBadGateway, "ML_SERVICE_UNAVAILABLE", "failed to call ML service")
		return
	}

	c.JSON(http.StatusOK, resp)
}

func newSessionID() string {
	buf := make([]byte, 12)
	if _, err := rand.Read(buf); err != nil {
		return "session-fallback"
	}
	return "session-" + hex.EncodeToString(buf)
}
