package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/ru-liquidity-sentinel/backend/internal/grpcclient"
)

var staticModules = []grpcclient.ModuleDefinition{
	{
		ModuleID:    "M1_RESERVES",
		ModuleName:  "Усреднение обязательных резервов",
		Description: "Оценивает напряжение через спред обязательных резервов и RUONIA.",
	},
	{
		ModuleID:    "M2_REPO",
		ModuleName:  "Аукционы репо ЦБ",
		Description: "Оценивает спрос банков на ликвидность через cover ratio и ставочные спреды.",
	},
	{
		ModuleID:    "M3_OFZ",
		ModuleName:  "Размещение ОФЗ",
		Description: "Оценивает спрос на государственные облигации и признаки недоспроса.",
	},
	{
		ModuleID:    "M4_TAX",
		ModuleName:  "Налоговый период и сезонность",
		Description: "Учитывает налоговые даты, конец месяца и квартала как сезонный фактор.",
	},
	{
		ModuleID:    "M5_TREASURY",
		ModuleName:  "Средства федерального казначейства",
		Description: "Отслеживает бюджетный канал притока и оттока ликвидности.",
	},
}

type ModulesHandler struct {
	liquidityClient *grpcclient.LiquidityClient
}

func NewModulesHandler(liquidityClient *grpcclient.LiquidityClient) *ModulesHandler {
	return &ModulesHandler{liquidityClient: liquidityClient}
}

func (h *ModulesHandler) ListModules(c *gin.Context) {
	c.JSON(http.StatusOK, grpcclient.ModulesListResponse{Modules: staticModules})
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

	resp, err := h.liquidityClient.GetModuleSignals(c.Request.Context(), moduleID, from, to)
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

	resp, err := h.liquidityClient.GetAllModulesSnapshot(c.Request.Context(), date)
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
