package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/ru-liquidity-sentinel/backend/internal/service"
)

type ModulesHandler struct {
	modulesService *service.ModulesService
}

func NewModulesHandler(modulesService *service.ModulesService) *ModulesHandler {
	return &ModulesHandler{modulesService: modulesService}
}

func (h *ModulesHandler) ListModules(c *gin.Context) {
	resp, err := h.modulesService.ListModules(c.Request.Context())
	if err != nil {
		writeError(c, http.StatusBadGateway, "ML_SERVICE_UNAVAILABLE", "failed to call ML service")
		return
	}
	c.JSON(http.StatusOK, resp)
}

func (h *ModulesHandler) GetSignals(c *gin.Context) {
	moduleID := c.Param("id")
	if !isValidModuleID(moduleID) {
		writeError(c, http.StatusBadRequest, "BAD_REQUEST", "invalid module_id")
		return
	}

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

	resp, err := h.modulesService.GetSignals(c.Request.Context(), moduleID, from, to)
	if err != nil {
		writeError(c, http.StatusBadGateway, "ML_SERVICE_UNAVAILABLE", "failed to call ML service")
		return
	}

	c.JSON(http.StatusOK, resp)
}

func (h *ModulesHandler) GetSnapshot(c *gin.Context) {
	date := c.Query("date")
	if date != "" && !validateDateString(date) {
		writeError(c, http.StatusBadRequest, "BAD_REQUEST", "date must be in YYYY-MM-DD format")
		return
	}

	resp, err := h.modulesService.GetSnapshot(c.Request.Context(), date)
	if err != nil {
		writeError(c, http.StatusBadGateway, "ML_SERVICE_UNAVAILABLE", "failed to call ML service")
		return
	}

	c.JSON(http.StatusOK, resp)
}

func isValidModuleID(value string) bool {
	switch value {
	case "M1_RESERVES", "M2_REPO", "M3_OFZ", "M4_TAX", "M5_TREASURY":
		return true
	default:
		return false
	}
}
