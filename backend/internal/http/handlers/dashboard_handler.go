package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/ru-liquidity-sentinel/backend/internal/service"
)

type DashboardHandler struct {
	dashboardService *service.DashboardService
}

func NewDashboardHandler(dashboardService *service.DashboardService) *DashboardHandler {
	return &DashboardHandler{dashboardService: dashboardService}
}

func (h *DashboardHandler) GetCurrentDashboard(c *gin.Context) {
	includeShap := parseBoolQuery(c, "include_shap", true)
	includeForecast := parseBoolQuery(c, "include_forecast", true)
	includeComment := parseBoolQuery(c, "include_comment", true)

	resp, err := h.dashboardService.GetCurrentDashboard(c.Request.Context(), includeShap, includeForecast, includeComment)
	if err != nil {
		writeError(c, http.StatusBadGateway, "ML_SERVICE_UNAVAILABLE", "failed to call ML service")
		return
	}

	c.JSON(http.StatusOK, resp)
}
