package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/ru-liquidity-sentinel/backend/internal/grpcclient"
)

type BacktestHandler struct {
	liquidityClient *grpcclient.LiquidityClient
}

func NewBacktestHandler(liquidityClient *grpcclient.LiquidityClient) *BacktestHandler {
	return &BacktestHandler{liquidityClient: liquidityClient}
}

func (h *BacktestHandler) GetBacktest(c *gin.Context) {
	episode, ok := requireQuery(c, "episode")
	if !ok {
		return
	}
	if !isValidEpisode(episode) {
		writeError(c, http.StatusBadRequest, "BAD_REQUEST", "invalid episode")
		return
	}

	from := c.Query("from")
	to := c.Query("to")
	if episode == "custom" {
		if !validateDateRange(from, to) {
			writeError(c, http.StatusBadRequest, "BAD_REQUEST", "custom episode requires valid from/to")
			return
		}
	}

	req := grpcclient.BacktestRequest{
		Episode:                episode,
		From:                   from,
		To:                     to,
		IncludeShap:            parseBoolQuery(c, "include_shap", true),
		IncludeModuleBreakdown: parseBoolQuery(c, "include_module_breakdown", true),
	}

	resp, err := h.liquidityClient.GetBacktest(c.Request.Context(), req)
	if err != nil {
		writeError(c, http.StatusBadGateway, "ML_SERVICE_UNAVAILABLE", "failed to call ML service")
		return
	}

	c.JSON(http.StatusOK, resp)
}

func isValidEpisode(value string) bool {
	switch value {
	case "december_2014", "february_march_2022", "august_2023", "custom":
		return true
	default:
		return false
	}
}
