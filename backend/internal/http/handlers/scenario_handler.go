package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/ru-liquidity-sentinel/backend/internal/grpcclient"
)

type ScenarioHandler struct {
	liquidityClient *grpcclient.LiquidityClient
}

func NewScenarioHandler(liquidityClient *grpcclient.LiquidityClient) *ScenarioHandler {
	return &ScenarioHandler{liquidityClient: liquidityClient}
}

func (h *ScenarioHandler) RunScenario(c *gin.Context) {
	var req grpcclient.ScenarioRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		writeError(c, http.StatusBadRequest, "BAD_REQUEST", "invalid request body")
		return
	}
	if !validateDateString(req.BaseDate) {
		writeError(c, http.StatusBadRequest, "BAD_REQUEST", "base_date is required and must be in YYYY-MM-DD format")
		return
	}
	if len(req.Shocks) == 0 {
		writeError(c, http.StatusBadRequest, "BAD_REQUEST", "shocks must not be empty")
		return
	}
	for _, shock := range req.Shocks {
		if shock.FeatureName == "" {
			writeError(c, http.StatusBadRequest, "BAD_REQUEST", "feature_name must not be empty")
			return
		}
		if !isValidModuleID(shock.ModuleID) {
			writeError(c, http.StatusBadRequest, "BAD_REQUEST", "invalid module_id")
			return
		}
	}

	resp, err := h.liquidityClient.RunScenario(c.Request.Context(), req)
	if err != nil {
		writeError(c, http.StatusBadGateway, "ML_SERVICE_UNAVAILABLE", "failed to call ML service")
		return
	}

	c.JSON(http.StatusOK, resp)
}
