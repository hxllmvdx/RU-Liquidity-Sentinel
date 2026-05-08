package grpcclient

import (
	pb "github.com/ru-liquidity-sentinel/backend/gen/go/liquidity/v1"
	"github.com/ru-liquidity-sentinel/backend/internal/dto"
)

func mapStatus(status pb.Status) string {
	switch status {
	case pb.Status_STATUS_GREEN:
		return "green"
	case pb.Status_STATUS_YELLOW:
		return "yellow"
	case pb.Status_STATUS_RED:
		return "red"
	default:
		return "unspecified"
	}
}

func parseStatus(value string) (pb.Status, bool) {
	switch value {
	case "green":
		return pb.Status_STATUS_GREEN, true
	case "yellow":
		return pb.Status_STATUS_YELLOW, true
	case "red":
		return pb.Status_STATUS_RED, true
	default:
		return pb.Status_STATUS_UNSPECIFIED, false
	}
}

func mapModuleID(moduleID pb.ModuleId) string {
	switch moduleID {
	case pb.ModuleId_MODULE_ID_M1_RESERVES:
		return "M1_RESERVES"
	case pb.ModuleId_MODULE_ID_M2_REPO:
		return "M2_REPO"
	case pb.ModuleId_MODULE_ID_M3_OFZ:
		return "M3_OFZ"
	case pb.ModuleId_MODULE_ID_M4_TAX:
		return "M4_TAX"
	case pb.ModuleId_MODULE_ID_M5_TREASURY:
		return "M5_TREASURY"
	default:
		return "UNSPECIFIED"
	}
}

func parseModuleID(value string) (pb.ModuleId, bool) {
	switch value {
	case "M1_RESERVES":
		return pb.ModuleId_MODULE_ID_M1_RESERVES, true
	case "M2_REPO":
		return pb.ModuleId_MODULE_ID_M2_REPO, true
	case "M3_OFZ":
		return pb.ModuleId_MODULE_ID_M3_OFZ, true
	case "M4_TAX":
		return pb.ModuleId_MODULE_ID_M4_TAX, true
	case "M5_TREASURY":
		return pb.ModuleId_MODULE_ID_M5_TREASURY, true
	default:
		return pb.ModuleId_MODULE_ID_UNSPECIFIED, false
	}
}

func mapEpisode(episode pb.StressEpisode) string {
	switch episode {
	case pb.StressEpisode_STRESS_EPISODE_DECEMBER_2014:
		return "december_2014"
	case pb.StressEpisode_STRESS_EPISODE_FEBRUARY_MARCH_2022:
		return "february_march_2022"
	case pb.StressEpisode_STRESS_EPISODE_AUGUST_2023:
		return "august_2023"
	case pb.StressEpisode_STRESS_EPISODE_CUSTOM:
		return "custom"
	default:
		return "unspecified"
	}
}

func parseEpisode(value string) (pb.StressEpisode, bool) {
	switch value {
	case "december_2014":
		return pb.StressEpisode_STRESS_EPISODE_DECEMBER_2014, true
	case "february_march_2022":
		return pb.StressEpisode_STRESS_EPISODE_FEBRUARY_MARCH_2022, true
	case "august_2023":
		return pb.StressEpisode_STRESS_EPISODE_AUGUST_2023, true
	case "custom":
		return pb.StressEpisode_STRESS_EPISODE_CUSTOM, true
	default:
		return pb.StressEpisode_STRESS_EPISODE_UNSPECIFIED, false
	}
}

func mapLSIResponse(resp *pb.LSIResponse) *dto.DashboardResponse {
	if resp == nil {
		return &dto.DashboardResponse{}
	}

	return &dto.DashboardResponse{
		Date:          resp.GetDate(),
		LSI:           resp.GetLsi(),
		Status:        mapStatus(resp.GetStatus()),
		Confidence:    resp.GetConfidence(),
		Contributions: mapContributions(resp.GetContributions()),
		ShapValues:    mapShapValues(resp.GetShapValues()),
		ActiveFlags:   mapActiveFlags(resp.GetActiveFlags()),
		Forecast:      mapForecast(resp.GetForecast()),
		AutoComment:   resp.GetAutoComment(),
	}
}

func mapContributions(items []*pb.ModuleContribution) []dto.ModuleContribution {
	result := make([]dto.ModuleContribution, 0, len(items))
	for _, item := range items {
		result = append(result, dto.ModuleContribution{
			ModuleID:            mapModuleID(item.GetModuleId()),
			ModuleName:          item.GetModuleName(),
			ContributionValue:   item.GetContributionValue(),
			ContributionPercent: item.GetContributionPercent(),
		})
	}
	return result
}

func mapShapValues(items []*pb.ShapValue) []dto.ShapValue {
	result := make([]dto.ShapValue, 0, len(items))
	for _, item := range items {
		result = append(result, dto.ShapValue{
			FeatureName: item.GetFeatureName(),
			ModuleID:    mapModuleID(item.GetModuleId()),
			Value:       item.GetValue(),
			AbsValue:    item.GetAbsValue(),
		})
	}
	return result
}

func mapActiveFlags(items []*pb.ActiveFlag) []dto.ActiveFlag {
	result := make([]dto.ActiveFlag, 0, len(items))
	for _, item := range items {
		result = append(result, dto.ActiveFlag{
			FlagName:    item.GetFlagName(),
			ModuleID:    mapModuleID(item.GetModuleId()),
			Description: item.GetDescription(),
			Severity:    item.GetSeverity(),
		})
	}
	return result
}

func mapForecast(items []*pb.ForecastPoint) []dto.ForecastPoint {
	result := make([]dto.ForecastPoint, 0, len(items))
	for _, item := range items {
		result = append(result, dto.ForecastPoint{
			Horizon:    item.GetHorizon(),
			TargetDate: item.GetTargetDate(),
			LSI:        item.GetLsi(),
			Status:     mapStatus(item.GetStatus()),
			Confidence: item.GetConfidence(),
		})
	}
	return result
}

func mapLSIHistoryResponse(resp *pb.GetLSIHistoryResponse) *dto.LSIHistoryResponse {
	if resp == nil {
		return &dto.LSIHistoryResponse{}
	}
	points := make([]dto.LSIHistoryPoint, 0, len(resp.GetPoints()))
	for _, point := range resp.GetPoints() {
		points = append(points, dto.LSIHistoryPoint{
			Date:       point.GetDate(),
			LSI:        point.GetLsi(),
			Status:     mapStatus(point.GetStatus()),
			Confidence: point.GetConfidence(),
		})
	}
	return &dto.LSIHistoryResponse{Points: points}
}

func mapRecalculateResponse(resp *pb.RecalculateLSIResponse) *dto.RecalculateResponse {
	if resp == nil {
		return &dto.RecalculateResponse{}
	}
	return &dto.RecalculateResponse{
		Result:         mapLSIResponse(resp.GetResult()),
		UpdatedSources: resp.GetUpdatedSources(),
	}
}

func mapModuleSignalsResponse(resp *pb.GetModuleSignalsResponse) *dto.ModuleSignalsResponse {
	if resp == nil {
		return &dto.ModuleSignalsResponse{}
	}
	signals := make([]dto.ModuleSignal, 0, len(resp.GetSignals()))
	for _, signal := range resp.GetSignals() {
		signals = append(signals, dto.ModuleSignal{
			Date:       signal.GetDate(),
			ModuleID:   mapModuleID(signal.GetModuleId()),
			SignalName: signal.GetSignalName(),
			RawValue:   signal.GetRawValue(),
			MadScore:   signal.GetMadScore(),
			Flag:       signal.GetFlag(),
			Unit:       signal.GetUnit(),
		})
	}
	return &dto.ModuleSignalsResponse{
		ModuleID:    mapModuleID(resp.GetModuleId()),
		Signals:     signals,
		ActiveFlags: mapActiveFlags(resp.GetActiveFlags()),
	}
}

func mapModulesSnapshotResponse(resp *pb.GetAllModulesSnapshotResponse) *dto.ModulesSnapshotResponse {
	if resp == nil {
		return &dto.ModulesSnapshotResponse{}
	}
	modules := make([]dto.ModuleSnapshot, 0, len(resp.GetModules()))
	for _, module := range resp.GetModules() {
		signals := make([]dto.ModuleSignal, 0, len(module.GetSignals()))
		for _, signal := range module.GetSignals() {
			signals = append(signals, dto.ModuleSignal{
				Date:       signal.GetDate(),
				ModuleID:   mapModuleID(signal.GetModuleId()),
				SignalName: signal.GetSignalName(),
				RawValue:   signal.GetRawValue(),
				MadScore:   signal.GetMadScore(),
				Flag:       signal.GetFlag(),
				Unit:       signal.GetUnit(),
			})
		}
		modules = append(modules, dto.ModuleSnapshot{
			ModuleID:    mapModuleID(module.GetModuleId()),
			ModuleName:  module.GetModuleName(),
			ModuleScore: module.GetModuleScore(),
			Signals:     signals,
			ActiveFlags: mapActiveFlags(module.GetActiveFlags()),
		})
	}
	return &dto.ModulesSnapshotResponse{
		Date:    resp.GetDate(),
		Modules: modules,
	}
}

func mapScenarioResponse(resp *pb.ScenarioResponse) *dto.ScenarioResponse {
	if resp == nil {
		return &dto.ScenarioResponse{}
	}
	return &dto.ScenarioResponse{
		BaseDate:             resp.GetBaseDate(),
		BaseLSI:              resp.GetBaseLsi(),
		BaseStatus:           mapStatus(resp.GetBaseStatus()),
		ScenarioLSI:          resp.GetScenarioLsi(),
		ScenarioStatus:       mapStatus(resp.GetScenarioStatus()),
		DeltaLSI:             resp.GetDeltaLsi(),
		ChangedContributions: mapContributions(resp.GetChangedContributions()),
		ScenarioShapValues:   mapShapValues(resp.GetScenarioShapValues()),
		Explanation:          resp.GetExplanation(),
	}
}

func mapBacktestResponse(resp *pb.BacktestResponse) *dto.BacktestResponse {
	if resp == nil {
		return &dto.BacktestResponse{}
	}
	history := make([]dto.LSIHistoryPoint, 0, len(resp.GetLsiHistory()))
	for _, point := range resp.GetLsiHistory() {
		history = append(history, dto.LSIHistoryPoint{
			Date:       point.GetDate(),
			LSI:        point.GetLsi(),
			Status:     mapStatus(point.GetStatus()),
			Confidence: point.GetConfidence(),
		})
	}
	metrics := make([]dto.BacktestMetric, 0, len(resp.GetMetrics()))
	for _, metric := range resp.GetMetrics() {
		metrics = append(metrics, dto.BacktestMetric{
			Name:  metric.GetName(),
			Value: metric.GetValue(),
			Unit:  metric.GetUnit(),
		})
	}
	events := make([]dto.BacktestEvent, 0, len(resp.GetEvents()))
	for _, event := range resp.GetEvents() {
		events = append(events, dto.BacktestEvent{
			Date:        event.GetDate(),
			Title:       event.GetTitle(),
			Description: event.GetDescription(),
			LSI:         event.GetLsi(),
			Status:      mapStatus(event.GetStatus()),
		})
	}
	result := &dto.BacktestResponse{
		Episode:              mapEpisode(resp.GetEpisode()),
		LSIHistory:           history,
		Metrics:              metrics,
		Events:               events,
		AverageContributions: mapContributions(resp.GetAverageContributions()),
		Conclusion:           resp.GetConclusion(),
	}
	if resp.GetRange() != nil {
		result.Range = dto.DateRange{
			From: resp.GetRange().GetFrom(),
			To:   resp.GetRange().GetTo(),
		}
	}
	return result
}

func mapAutoCommentResponse(resp *pb.AutoCommentResponse) *dto.AutoCommentResponse {
	if resp == nil {
		return &dto.AutoCommentResponse{}
	}
	return &dto.AutoCommentResponse{
		Comment:       resp.GetComment(),
		Retrospective: resp.GetRetrospective(),
		Outlook:       resp.GetOutlook(),
	}
}

func mapChatResponse(resp *pb.ChatResponse) *dto.ChatResponse {
	if resp == nil {
		return &dto.ChatResponse{}
	}
	contexts := make([]dto.ChatContext, 0, len(resp.GetContexts()))
	for _, item := range resp.GetContexts() {
		contexts = append(contexts, dto.ChatContext{
			SourceType: item.GetSourceType(),
			Title:      item.GetTitle(),
			Content:    item.GetContent(),
			Relevance:  item.GetRelevance(),
		})
	}
	return &dto.ChatResponse{
		SessionID: resp.GetSessionId(),
		Answer:    resp.GetAnswer(),
		Contexts:  contexts,
	}
}
