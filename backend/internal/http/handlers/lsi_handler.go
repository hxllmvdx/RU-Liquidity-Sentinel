package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/ru-liquidity-sentinel/backend/internal/dto"
	"github.com/ru-liquidity-sentinel/backend/internal/service"
)

type LSIHandler struct {
	lsiService *service.LSIService
}

func NewLSIHandler(lsiService *service.LSIService) *LSIHandler {
	return &LSIHandler{lsiService: lsiService}
}

func (h *LSIHandler) GetHistory(c *gin.Context) {
	from, ok := requireQuery(c, "from")
	if !ok {
		return
	}
	to, ok := requireQuery(c, "to")
	if !ok {
		return
	}
	if !validateDateRange(from, to) {
		writeError(c, http.StatusBadRequest, "BAD_REQUEST", "invalid date range")
		return
	}

	limit, err := parseIntQuery(c, "limit", 500)
	if err != nil || limit <= 0 || limit > 5000 {
		writeError(c, http.StatusBadRequest, "BAD_REQUEST", "limit must be > 0 and <= 5000")
		return
	}
	offset, err := parseIntQuery(c, "offset", 0)
	if err != nil || offset < 0 {
		writeError(c, http.StatusBadRequest, "BAD_REQUEST", "offset must be >= 0")
		return
	}

	resp, grpcErr := h.lsiService.GetHistory(c.Request.Context(), from, to, limit, offset)
	if grpcErr != nil {
		writeError(c, http.StatusBadGateway, "ML_SERVICE_UNAVAILABLE", "failed to call ML service")
		return
	}

	c.JSON(http.StatusOK, resp)
}

func (h *LSIHandler) Recalculate(c *gin.Context) {
	var req dto.RecalculateRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		writeError(c, http.StatusBadRequest, "BAD_REQUEST", "invalid request body")
		return
	}
	if req.Date != "" && !validateDateString(req.Date) {
		writeError(c, http.StatusBadRequest, "BAD_REQUEST", "date must be in YYYY-MM-DD format")
		return
	}

	resp, err := h.lsiService.Recalculate(c.Request.Context(), req)
	if err != nil {
		writeError(c, http.StatusBadGateway, "ML_SERVICE_UNAVAILABLE", "failed to call ML service")
		return
	}

	c.JSON(http.StatusOK, resp)
}
